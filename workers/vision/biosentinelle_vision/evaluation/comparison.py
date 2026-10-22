"""Comparaison intrinsèque sur les mêmes crops, sans sélection sur le test."""

import hashlib
import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from ..classes import ClassManifest
from ..classification.contracts import ModelVersion
from ..classification.factory import load_classifier
from ..datasets.benchmark import canonical
from ..datasets.inventory import file_hash
from ..errors import ManifestError
from ..schemas import CropsManifest
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from .metrics import classification_metrics


def metrics_with_abstentions(
    truth: list[str], predicted: list[str | None], classes: ClassManifest
) -> dict[str, Any]:
    pairs = [(a, b) for a, b in zip(truth, predicted, strict=True) if b is not None]
    metrics = classification_metrics([a for a, _ in pairs], [b for _, b in pairs], classes)
    supports = Counter(truth)
    correct = sum(a == b for a, b in zip(truth, predicted, strict=True))
    for i, name in enumerate(classes.names):
        entry = metrics["per_class"][name]
        tp = metrics["confusion_matrix"][i][i]
        entry["support"] = supports[name]
        entry["recall"] = tp / supports[name] if supports[name] else 0.0
        precision, recall = entry["precision"], entry["recall"]
        entry["f1"] = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    metrics.update(
        count=len(truth),
        accuracy=correct / len(truth) if truth else None,
        macro_f1=sum(m["f1"] for m in metrics["per_class"].values()) / len(classes.names)
        if truth
        else None,
        macro_recall=sum(m["recall"] for m in metrics["per_class"].values()) / len(classes.names)
        if truth
        else None,
        absent_classes=[name for name in classes.names if not supports[name]],
        abstentions=dict(Counter(a for a, b in zip(truth, predicted, strict=True) if b is None)),
    )
    return metrics


def compare_classifiers(
    manifest: Path,
    storage_root: Path,
    versions: list[ModelVersion],
    output: Path,
    classes: ClassManifest,
    *,
    split: str = "val",
    threshold: float = 0.48,
    batch_size: int = 2,
    device: str = "cpu",
    lock: Path,
    video_truth: dict[str, str] | None = None,
    allow_weak_labels: bool = False,
    check_cancelled: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    if (
        split not in ("val", "test")
        or len(versions) < 1
        or len({v.model_id for v in versions}) != len(versions)
    ):
        raise ManifestError("Comparaison : split val/test et identifiants uniques requis")
    if batch_size < 1 or not 0 <= threshold <= 1:
        raise ManifestError("Paramètres de comparaison invalides")
    source = CropsManifest.model_validate_json(manifest.read_text(encoding="utf-8"))
    if source.class_manifest_version != classes.version:
        raise ManifestError("Référentiel de comparaison incompatible")
    records = sorted(
        (r for r in source.crops if r.frame.split == split and r.review != "reject"),
        key=lambda r: r.crop_id,
    )
    if not records or any(r.review != "accept" for r in records) and not allow_weak_labels:
        raise ManifestError("Une comparaison exige des recadrages validés humainement")
    truth = [r.label or r.frame.species_candidate for r in records]
    if any(label not in classes.names for label in truth):
        raise ManifestError("Label de comparaison inconnu")
    storage = LocalStorage(storage_root)
    dataset_version = hashlib.sha256(
        canonical(
            [
                {
                    "record": r.model_dump(mode="json"),
                    "sha256": file_hash(storage.path(r.image_key)),
                }
                for r in records
            ]
        )
    ).hexdigest()
    protocol = {
        "split": split,
        "scope": "classifier_on_fixed_crops",
        "threshold": threshold,
        "aggregation": "mean_probability_per_video_v1",
        "batch_size": batch_size,
        "class_manifest_version": classes.version,
    }
    model_results = []
    for version in versions:
        check_cancelled()
        with exclusive_gpu(device, lock):
            classifier = None
            began = time.perf_counter()
            predictions, times, peak, failure = [], [], None, None
            try:
                classifier = load_classifier(
                    version, classes, device=device, threshold=threshold, batch_size=batch_size
                )
                loaded = time.perf_counter() - began
                if device == "cuda":
                    import torch

                    torch.cuda.reset_peak_memory_stats()
                for start in range(0, len(records), batch_size):
                    check_cancelled()
                    images = []
                    for record in records[start : start + batch_size]:
                        with Image.open(storage.path(record.image_key)) as image:
                            images.append(image.convert("RGB"))
                    began_batch = time.perf_counter()
                    batch = classifier.predict_batch(images)
                    if len(batch) != len(images):
                        raise ManifestError("Nombre de résultats incompatible")
                    times.extend(
                        [(time.perf_counter() - began_batch) * 1000 / len(batch)] * len(batch)
                    )
                    predictions.extend(batch)
                if device == "cuda":
                    peak = torch.cuda.max_memory_allocated()
            except Exception as exc:
                failure = f"{type(exc).__name__}: {exc}"
                loaded = time.perf_counter() - began
            finally:
                if classifier is not None:
                    classifier.unload()
            if len(predictions) != len(records):
                predictions = []
            rows, raw_labels, operating = [], [], []
            by_video: dict[str, list[list[float]]] = defaultdict(list)
            for index, record in enumerate(records):
                prediction = predictions[index] if predictions else None
                valid = prediction is not None and prediction.status != "error"
                scores = [prediction.scores[name] for name in classes.names] if valid else None
                raw_label = (
                    classes.names[max(range(len(scores)), key=scores.__getitem__)]
                    if scores
                    else None
                )
                raw_labels.append(raw_label)
                operating.append(
                    prediction.species_slug if valid and prediction.status == "recognized" else None
                )
                if scores:
                    by_video[record.frame.video_id].append(scores)
                rows.append(
                    {
                        "crop_id": record.crop_id,
                        "video_id": record.frame.video_id,
                        "truth": truth[index],
                        "predicted": raw_label,
                        "scores": scores,
                        "status": prediction.status if prediction else "error",
                    }
                )
            v_truth, v_pred = [], []
            for identifier in sorted({r.frame.video_id for r in records}):
                if identifier not in (video_truth or {}):
                    continue
                v_truth.append(video_truth[identifier])
                votes = by_video.get(identifier, [])
                mean = (
                    [sum(p[i] for p in votes) / len(votes) for i in range(len(classes.names))]
                    if votes
                    else []
                )
                v_pred.append(
                    classes.names[max(range(len(mean)), key=mean.__getitem__)] if mean else None
                )
            size = version.checkpoint.stat().st_size if version.checkpoint.is_file() else None
            if version.classifier_family == "embedding" and version.checkpoint.is_file():
                descriptor = json.loads(version.checkpoint.read_text(encoding="utf-8"))
                size += (
                    LocalStorage(version.checkpoint.parent)
                    .path(descriptor["model_key"])
                    .stat()
                    .st_size
                )
                from ..classification.pretrained import load_asset

                _, extractor_weights = load_asset(Path(descriptor["pretrained_manifest"]))
                size += extractor_weights.stat().st_size
            model_results.append(
                {
                    "model": version.model_dump(mode="json"),
                    "checkpoint_sha256": file_hash(version.checkpoint)
                    if version.checkpoint.is_file()
                    else None,
                    "metrics": metrics_with_abstentions(truth, raw_labels, classes),
                    "operating_metrics": metrics_with_abstentions(truth, operating, classes),
                    "videos": metrics_with_abstentions(v_truth, v_pred, classes),
                    "coverage": sum(p is not None for p in operating) / len(records),
                    "failure_rate": sum(r["status"] == "error" for r in rows) / len(records),
                    "mean_inference_ms": sum(times) / len(times) if times else None,
                    "load_seconds": loaded,
                    "gpu_peak_allocated_bytes": peak,
                    "model_bytes": size,
                    "predictions": rows,
                    "error": failure,
                }
            )
    support = {
        name: len(
            {r.frame.video_id for r, label in zip(records, truth, strict=True) if label == name}
        )
        for name in classes.names
    }
    report = {
        "schema_version": "classifier-comparison-1",
        "dataset_version": dataset_version,
        "protocol": protocol,
        "classes": classes.model_dump(mode="json"),
        "human_validated": all(r.review == "accept" for r in records),
        "video_support": support,
        "models": model_results,
        "warnings": [
            f"{name} : {n} vidéos, incertitude statistique élevée"
            for name, n in support.items()
            if n < 3
        ],
        "note": "Classification sur crops ; pas une mesure de performance du détecteur.",
    }
    LocalStorage(output.parent).write_json(output.name, report)
    return report
