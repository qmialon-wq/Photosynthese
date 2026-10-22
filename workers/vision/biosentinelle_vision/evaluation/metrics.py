from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from ..classes import ClassManifest
from ..classification.model import prediction_from_probabilities
from ..errors import ManifestError
from ..schemas import PredictionsManifest


def classification_metrics(
    truth: Sequence[str],
    predicted: Sequence[str],
    classes: ClassManifest,
) -> dict[str, Any]:
    if len(truth) != len(predicted):
        raise ManifestError("Vérités et prédictions de tailles différentes")
    index = {name: i for i, name in enumerate(classes.names)}
    matrix = [[0 for _ in index] for _ in index]
    for actual, prediction in zip(truth, predicted, strict=True):
        if actual not in index or prediction not in index:
            raise ManifestError("Espèce inconnue dans l'évaluation")
        matrix[index[actual]][index[prediction]] += 1
    per_class = {}
    for name, i in index.items():
        tp = matrix[i][i]
        support = sum(matrix[i])
        positives = sum(row[i] for row in matrix)
        precision = tp / positives if positives else 0.0
        recall = tp / support if support else 0.0
        per_class[name] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": 2 * tp / (support + positives) if support + positives else 0.0,
        }
    return {
        "count": len(truth),
        "accuracy": sum(matrix[i][i] for i in index.values()) / len(truth) if truth else None,
        "macro_f1": sum(m["f1"] for m in per_class.values()) / len(index) if truth else None,
        "classes": list(classes.names),
        "confusion_matrix": matrix,
        "per_class": per_class,
        "absent_classes": [name for name, m in per_class.items() if not m["support"]],
    }


def evaluate_predictions(
    source: PredictionsManifest,
    classes: ClassManifest,
) -> dict[str, Any]:
    if source.class_manifest_version != classes.version or source.classes != classes.names:
        raise ManifestError("Manifeste de classes incompatible pour l'évaluation")
    if not source.predictions:
        raise ManifestError("Aucune prédiction à évaluer")
    if len({row.crop_id for row in source.predictions}) != len(source.predictions):
        raise ManifestError("Prédictions de crops dupliquées")
    truth, predicted = [], []
    by_video: dict[str, list[tuple[float, ...]]] = defaultdict(list)
    for row in source.predictions:
        if not row.human_validated:
            raise ManifestError("Évaluation interdite sur un label non validé humainement")
        prediction = prediction_from_probabilities(row.probabilities, classes, threshold=0)
        truth.append(row.truth)
        predicted.append(prediction.label)
        by_video[row.video_id].append(row.probabilities)
    video_truth, video_predicted, omitted = [], [], []
    for video_id, probabilities in sorted(by_video.items()):
        if video_id not in source.video_truth:
            omitted.append(video_id)
            continue
        mean = [
            sum(p[i] for p in probabilities) / len(probabilities) for i in range(len(classes.names))
        ]
        video_truth.append(source.video_truth[video_id])
        video_predicted.append(prediction_from_probabilities(mean, classes, threshold=0).label)
    return {
        "schema_version": "1",
        "class_manifest_version": classes.version,
        "crops": classification_metrics(truth, predicted, classes),
        "videos": classification_metrics(video_truth, video_predicted, classes),
        "videos_without_human_truth": omitted,
    }
