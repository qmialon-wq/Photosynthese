from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from ..classes import ClassManifest
from ..errors import ManifestError
from ..evaluation.metrics import classification_metrics
from ..schemas import CropRecord


def aggregate_metrics(
    records: Sequence[CropRecord],
    probabilities: Sequence[Sequence[float]],
    classes: ClassManifest,
    video_truth: dict[str, str],
) -> dict[str, Any]:
    if not records or len(records) != len(probabilities):
        raise ManifestError("Évaluation vide ou nombres de prédictions incompatibles")
    if any(label not in classes.names for label in video_truth.values()):
        raise ManifestError("Vérité vidéo d'espèce inconnue")
    by_video: dict[str, list[Sequence[float]]] = defaultdict(list)
    actual, predicted = [], []
    for record, p in zip(records, probabilities, strict=True):
        if len(p) != len(classes.names):
            raise ManifestError("Distribution incompatible avec le manifeste des classes")
        actual.append(record.label)
        predicted.append(classes.names[max(range(len(p)), key=p.__getitem__)])
        by_video[record.frame.video_id].append(p)
    v_actual, v_predicted, omitted = [], [], []
    for video, rows in sorted(by_video.items()):
        if video not in video_truth:
            omitted.append(video)
            continue
        mean = [sum(row[i] for row in rows) / len(rows) for i in range(len(classes.names))]
        v_actual.append(video_truth[video])
        v_predicted.append(classes.names[max(range(len(mean)), key=mean.__getitem__)])
    images = classification_metrics(actual, predicted, classes)
    return {
        **images,
        "images": images,
        "videos": classification_metrics(v_actual, v_predicted, classes),
        "videos_without_human_truth": omitted,
        "human_validated": all(record.review == "accept" for record in records),
    }


def load_video_truth(path: Any, classes: ClassManifest) -> dict[str, str]:
    import json

    if path is None:
        return {}
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("class_manifest_version") != classes.version:
        raise ManifestError("Vérité vidéo incompatible avec les classes")
    truth = source.get("video_truth")
    if not isinstance(truth, dict) or any(
        not isinstance(k, str) or v not in classes.names for k, v in truth.items()
    ):
        raise ManifestError("Fournir video_truth comme dictionnaire vidéo -> espèce vérifiée")
    if source.get("human_validated") is not True:
        raise ManifestError("La vérité vidéo doit être explicitement validée humainement")
    return truth


def evaluate_loader(
    model: Any,
    loader: Any,
    device: str,
    loss_fn: Any,
    classes: ClassManifest,
    records: Sequence[CropRecord],
    video_truth: dict[str, str],
    amp_dtype: Any = None,
) -> dict[str, Any]:
    import torch

    probabilities, loss_sum, count = [], 0.0, 0
    model.eval()
    with torch.inference_mode():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            with torch.autocast(device, dtype=amp_dtype, enabled=amp_dtype is not None):
                logits = model(images)
                loss = loss_fn(logits, labels)
            loss_sum += float(loss.item()) * len(labels)
            count += len(labels)
            probabilities.extend(logits.float().softmax(-1).cpu().tolist())
    metrics = aggregate_metrics(records, probabilities, classes, video_truth)
    return {**metrics, "loss": loss_sum / count}
