"""Sélection sur validation, calibration SVM groupée, aucun apprentissage sur test."""

import hashlib
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from ..classes import load_classes
from ..classification.embeddings import read_embeddings
from ..classification.pretrained import freeze_asset, load_asset
from ..datasets.benchmark import canonical
from ..errors import ManifestError
from ..evaluation.metrics import classification_metrics
from ..storage import LocalStorage


def train_embedding_classifier(
    index: Path,
    output: Path,
    pretrained_manifest: Path,
    *,
    candidates: tuple[str, ...] = ("logistic", "knn", "linear_svm"),
    seed: int = 42,
    allow_weak_validation: bool = False,
    check_cancelled: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise ManifestError("La version de modèle existe déjà ; choisir un nouveau dossier")
    import joblib
    import numpy as np
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import Normalizer, StandardScaler
    from sklearn.svm import SVC, LinearSVC

    classes = load_classes()
    data, features = read_embeddings(index)
    pretrained, _ = load_asset(pretrained_manifest)
    if data["extractor"].get("weights_sha256") != pretrained["sha256"]:
        raise ManifestError("Extracteur différent de celui des embeddings")
    if data["classes"] != classes.model_dump(mode="json"):
        raise ManifestError("Ordre des classes incompatible")
    rows = data["samples"]
    labels = np.asarray([classes.names.index(row["label"]) for row in rows])
    splits = np.asarray([row["split"] for row in rows])
    train, validation = splits == "train", splits == "val"
    if not train.any() or not validation.any() or len(set(labels[train])) < 2:
        raise ManifestError("Train et validation non vides et au moins deux classes train requis")
    if not allow_weak_validation and any(
        not row["human_validated"] for row in rows if row["split"] == "val"
    ):
        raise ManifestError(
            "La sélection exige une validation humaine ; mode faible uniquement explicite"
        )
    groups = np.asarray([row["group_id"] for row in rows])
    for group in set(groups):
        if len(set(splits[groups == group])) != 1:
            raise ManifestError("Fuite de groupe entre splits")
    by_video: dict[str, set[str]] = {}
    by_content: dict[str, set[str]] = {}
    for row in rows:
        by_video.setdefault(row["video_id"], set()).add(row["split"])
        by_content.setdefault(row["image_sha256"], set()).add(row["split"])
    if any(len(s) != 1 for s in by_video.values()):
        raise ManifestError("Fuite de vidéo entre splits")
    if any(len(s) != 1 for s in by_content.values()):
        raise ManifestError("Fuite d'image identique entre splits")
    search, skipped, best, best_score = [], [], None, -1.0
    for algorithm in candidates:
        check_cancelled()
        if algorithm not in ("logistic", "knn", "linear_svm", "rbf_svm"):
            raise ManifestError(f"Algorithme inconnu : {algorithm}")
        for value in (1, 3, 5) if algorithm == "knn" else (0.1, 1.0, 10.0):
            check_cancelled()
            if algorithm == "knn":
                if value > int(train.sum()):
                    continue
                model = make_pipeline(
                    Normalizer(), KNeighborsClassifier(n_neighbors=value, weights="distance")
                )
            elif algorithm == "logistic":
                model = make_pipeline(
                    StandardScaler(), LogisticRegression(C=value, max_iter=2000, random_state=seed)
                )
            else:
                if algorithm == "rbf_svm" and int(train.sum()) > 5000:
                    skipped.append({"algorithm": algorithm, "reason": "RBF limité à 5000 exemples"})
                    break
                min_groups = min(
                    len(set(groups[train & (labels == label)])) for label in set(labels[train])
                )
                folds = min(3, min_groups)
                if folds < 2:
                    skipped.append(
                        {
                            "algorithm": algorithm,
                            "reason": "Calibration impossible : classe avec moins de deux groupes",
                        }
                    )
                    break
                cv = list(
                    StratifiedGroupKFold(folds, shuffle=True, random_state=seed).split(
                        features[train], labels[train], groups[train]
                    )
                )
                if any(
                    set(labels[train][a]) != set(labels[train])
                    or set(labels[train][b]) != set(labels[train])
                    for a, b in cv
                ):
                    skipped.append(
                        {"algorithm": algorithm, "reason": "Classe absente d'un pli de calibration"}
                    )
                    break
                estimator = (
                    LinearSVC(C=value, random_state=seed, max_iter=5000)
                    if algorithm == "linear_svm"
                    else SVC(C=value, kernel="rbf", probability=False, random_state=seed)
                )
                model = CalibratedClassifierCV(
                    make_pipeline(StandardScaler(), estimator), cv=cv, method="sigmoid"
                )
            model.fit(features[train], labels[train])
            check_cancelled()
            predicted = model.predict(features[validation])
            metrics = classification_metrics(
                [classes.names[i] for i in labels[validation]],
                [classes.names[i] for i in predicted],
                classes,
            )
            search.append({"algorithm": algorithm, "parameter": value, "metrics": metrics})
            if metrics["macro_f1"] > best_score:
                best, best_score = model, metrics["macro_f1"]
                chosen = search[-1]
    if best is None:
        raise ManifestError("Aucun candidat classique entraînable avec ces groupes")
    # Aucun refit sur validation ; les probabilités et transformations restent apprises sur train.
    storage = LocalStorage(output)
    buffer = BytesIO()
    joblib.dump(best, buffer)
    payload = buffer.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    storage.write_bytes("classifier.joblib", payload)
    metadata = {
        "schema_version": "embedding-classifier-1",
        "classes": classes.model_dump(mode="json"),
        "model_key": "classifier.joblib",
        "model_sha256": digest,
        "pretrained_manifest": str(freeze_asset(pretrained_manifest)),
        "extractor": data["extractor"],
        "dataset_version": hashlib.sha256(canonical(data)).hexdigest(),
        "selection": chosen,
        "search": search,
        "skipped": skipped,
        "seed": seed,
        "weak_validation": any(not r["human_validated"] for r in rows if r["split"] == "val"),
        "probability_kind": "calibrated_sigmoid"
        if chosen["algorithm"].endswith("svm")
        else "neighbor_vote"
        if chosen["algorithm"] == "knn"
        else "multinomial_logistic",
    }
    storage.write_json("model.json", metadata)
    return {"checkpoint": str(storage.path("model.json")), "selection": chosen, "skipped": skipped}
