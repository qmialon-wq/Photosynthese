import gc
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from ..classes import ClassManifest
from ..classification.model import TorchClassifier
from ..config import VisionSettings
from ..errors import ManifestError, ModelError
from ..schemas import CropsManifest
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from .dataset import select_samples
from .evaluation import aggregate_metrics, load_video_truth


def enqueue_training(
    settings: VisionSettings,
    kind: Literal["train_classifier", "evaluate_classifier"] = "train_classifier",
    split: Literal["train", "val", "test"] = "test",
) -> dict[str, Any]:
    from redis import Redis
    from redis.exceptions import RedisError

    from shared.vision_jobs import JobStore, TrainingRequest

    # Pas de lecture des images, d'initialisation CUDA ou de poids dans le client.
    try:
        with Redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        ) as client:
            return JobStore(client).enqueue(
                TrainingRequest(
                    kind=kind, split=split, configuration=settings.model_dump(mode="json")
                )
            )
    except RedisError as exc:
        raise ModelError(
            "File Redis indisponible ; démarrer les services ML avant de soumettre"
        ) from exc


def evaluate_classifier(
    settings: VisionSettings, classes: ClassManifest, split: str = "test"
) -> dict[str, Any]:
    if settings.train_manifest is None or settings.classifier_checkpoint is None:
        raise ManifestError("Fournir un manifeste de recadrages et un checkpoint")
    if settings.classifier_version is not None:
        from ..evaluation.comparison import compare_classifiers

        report = compare_classifiers(
            settings.train_manifest,
            settings.output_root,
            [settings.classifier_version],
            settings.output_root / "classifier_evaluation_comparison.json",
            classes,
            split=split,
            threshold=settings.classification_threshold,
            batch_size=settings.training.batch_size,
            device=settings.device,
            lock=settings.gpu_lock_path,
            video_truth=load_video_truth(settings.training.video_truth_manifest, classes),
        )
        row = report["models"][0]
        result = {
            **row["metrics"],
            "images": row["metrics"],
            "videos": row["videos"],
            "human_validated": report["human_validated"],
            "split": split,
            "checkpoint": row["model"],
            "operating_metrics": row["operating_metrics"],
            "error": row["error"],
        }
        LocalStorage(settings.output_root).write_json("classifier_evaluation.json", result)
        return result
    source = CropsManifest.model_validate_json(settings.train_manifest.read_text(encoding="utf-8"))
    if source.class_manifest_version != classes.version:
        raise ManifestError("Manifeste incompatible avec les classes")
    samples = [
        r
        for r in select_samples(source.crops, classes, settings.crops.max_per_video)
        if r.frame.split == split
    ]
    if not samples:
        raise ManifestError(f"Aucun crop {split} validé humainement")
    truth = load_video_truth(settings.training.video_truth_manifest, classes)
    storage = LocalStorage(settings.output_root)
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        classifier = TorchClassifier(
            settings.classifier_checkpoint,
            classes,
            device=settings.device,
            threshold=0,
            batch_size=settings.training.batch_size,
        )
        import torch

        probabilities, index = [], 0
        try:
            while index < len(samples):
                batch = samples[index : index + classifier.batch_size]
                images = []
                for record in batch:
                    with Image.open(BytesIO(storage.read_bytes(record.image_key))) as image:
                        images.append(image.convert("RGB"))
                try:
                    predictions = classifier.predict(images)
                except torch.OutOfMemoryError as exc:
                    if classifier.batch_size == 1:
                        raise ModelError("Évaluation OOM même avec batch=1") from exc
                    classifier.batch_size = max(1, classifier.batch_size // 2)
                    gc.collect()
                    if settings.device == "cuda":
                        torch.cuda.empty_cache()
                    continue
                probabilities.extend(p.probabilities for p in predictions)
                index += len(batch)
            report = {
                "split": split,
                "class_manifest_version": classes.version,
                "checkpoint": classifier.metadata,
                **aggregate_metrics(samples, probabilities, classes, truth),
            }
        finally:
            del classifier
            gc.collect()
            if settings.device == "cuda":
                torch.cuda.empty_cache()
    storage.write_json("classifier_evaluation.json", report)
    return report


def sync_metrics(directory: Path) -> None:
    from shared.training_metrics import project_run

    metadata = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    history = json.loads((directory / "history.json").read_text(encoding="utf-8"))
    project_run(metadata, history)
    LocalStorage(directory).write_json("database_sync.json", {"status": "ok"})
