"""Orchestration explicite des commandes locales, indépendante de Redis et HTTP."""

import gc
import hashlib
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

from PIL import Image

from .classes import ClassManifest
from .classification.base import Classifier
from .config import VisionSettings
from .datasets.inventory import VIDEO_EXTENSIONS, file_hash
from .detection.base import Detector
from .errors import GpuBusyError, ManifestError, ModelError, VideoError
from .inference.video import _analyze_video
from .schemas import CropRecord, CropsManifest
from .storage import LocalStorage
from .storage.gpu import exclusive_gpu
from .tracking.iou import IoUTracker
from .training.dataset import select_samples

logger = logging.getLogger(__name__)


def training_samples(settings: VisionSettings, classes: ClassManifest) -> tuple[CropRecord, ...]:
    path = settings.train_manifest or settings.output_root / "review.json"
    if not path.is_file():
        raise ManifestError(
            f"Manifeste de revue absent : {path}. Exécuter make prepare-training, puis make train "
            "pour utiliser les labels provisoires des noms, ou fournir une revue humaine."
        )
    manifest = CropsManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if manifest.class_manifest_version != classes.version:
        raise ManifestError("Manifeste de revue incompatible avec les classes")
    samples = select_samples(
        manifest.crops,
        classes,
        settings.crops.max_per_video,
        allow_filename_labels=settings.training.allow_filename_labels,
    )
    missing = set(classes.names) - {r.label for r in samples if r.frame.split == "train"}
    if missing or not any(r.frame.split == "val" for r in samples):
        raise ManifestError(f"Validation vide ou classes sans train validé : {sorted(missing)}")
    storage = LocalStorage(settings.output_root)
    for record in samples:
        if record.frame.split in ("train", "val"):
            try:
                with Image.open(storage.path(record.image_key)) as image:
                    image.verify()
            except (OSError, ValueError) as exc:
                raise ManifestError(f"Crop illisible : {record.image_key}") from exc
    if settings.initial_checkpoint is not None and not settings.initial_checkpoint.is_file():
        raise ModelError(f"Checkpoint initial absent : {settings.initial_checkpoint}")
    return samples


def train_from_manifest(
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event | None = None,
) -> dict[str, Any]:
    from .training.engine import train

    samples = training_samples(settings, classes)
    try:
        return train(
            samples,
            LocalStorage(settings.output_root),
            classes,
            settings,
            initial_checkpoint=settings.initial_checkpoint,
            stop=stop,
        )
    except ImportError as exc:
        raise ModelError("Dépendances ML absentes : construire l'image avec make ml-build") from exc


def input_videos(settings: VisionSettings) -> tuple[Path, ...]:
    root = settings.inbox_root.resolve()
    if not root.is_dir():
        raise VideoError(f"Dossier d'entrée absent : {root}. Exécuter make ml-init.")
    if settings.analysis_video:
        path = (root / settings.analysis_video).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise VideoError("La vidéo demandée doit être un fichier du dossier inbox")
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise VideoError("Extension vidéo non supportée")
        return (path,)
    return tuple(
        p
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p.resolve().is_relative_to(root)
        and p.suffix.lower() in VIDEO_EXTENSIONS
        and not p.name.startswith(".")
    )


def _weights(settings: VisionSettings) -> tuple[Path, Path | None]:
    detector, classifier = settings.detector_weights, settings.classifier_checkpoint
    if detector is None or not detector.is_file():
        raise ModelError(f"Poids MegaDetector locaux absents : {detector}")
    if not settings.detection_only and (classifier is None or not classifier.is_file()):
        raise ModelError(f"Checkpoint classificateur absent : {classifier}. Exécuter make train.")
    return detector, None if settings.detection_only else classifier


def _load_models(
    settings: VisionSettings, classes: ClassManifest
) -> tuple[Detector, Classifier | None]:
    from .classification.model import TorchClassifier
    from .detection.megadetector import MegaDetector

    detector_path, classifier_path = _weights(settings)
    return (
        MegaDetector(detector_path, settings),
        None
        if classifier_path is None
        else TorchClassifier(
            classifier_path,
            classes,
            device=settings.device,
            threshold=settings.classification_threshold,
            batch_size=settings.training.batch_size,
        ),
    )


def run_analyses(
    videos: tuple[Path, ...],
    settings: VisionSettings,
    classes: ClassManifest,
) -> list[dict[str, Any]]:
    if not videos:
        return []
    # Le verrou englobe aussi le chargement et la libération des modèles CUDA.
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        detector_path, classifier_path = _weights(settings)
        identity = {
            "pipeline_version": "2",
            "detector": file_hash(detector_path),
            "classifier": file_hash(classifier_path) if classifier_path is not None else None,
            "classes": classes.model_dump(mode="json"),
            "threshold": settings.classification_threshold,
            "detection_threshold": settings.detection_threshold,
            "stride": settings.infer_every_n_frames,
            "crops": settings.crops.model_dump(),
            "tracking": settings.tracking.model_dump(),
        }
        storage = LocalStorage(settings.output_root)
        detector, classifier = None, None
        results = []
        try:
            for video in videos:
                relative = video.resolve().relative_to(settings.inbox_root.resolve()).as_posix()
                before = video.stat()
                source_hash = file_hash(video)
                job = {**identity, "source": relative, "source_hash": source_hash}
                digest = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()[:16]
                prefix = f"analyses/{video.stem}-{digest}"
                state_key = f"{prefix}/state.json"
                state_path = storage.path(state_key)
                if state_path.is_file() and not settings.analysis_force:
                    previous = json.loads(storage.read_bytes(state_key))
                    artifacts_exist = (
                        storage.path(f"{prefix}/annotated.mp4").is_file()
                        and storage.path(f"{prefix}/report.json").is_file()
                        and storage.path(f"{prefix}/statistics.json").is_file()
                    )
                    if previous["status"] == "error" or artifacts_exist:
                        results.append({**previous, "skipped": True})
                        continue
                if detector is None:
                    detector, classifier = _load_models(settings, classes)
                logger.info("Analyse de %s", relative)
                state: dict[str, Any] = {
                    "source": relative,
                    "source_hash": source_hash,
                    "output": prefix,
                    "detector_hash": identity["detector"],
                    "classifier_hash": identity["classifier"],
                }
                try:
                    # Fonction interne : le verrou de la fonction publique est déjà détenu ici.
                    _analyze_video(
                        video,
                        detector,
                        classifier,
                        IoUTracker(classes, settings.tracking),
                        classes,
                        storage,
                        settings,
                        f"{prefix}/annotated.mp4",
                        f"{prefix}/report.json",
                    )
                    after = video.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise VideoError(
                            "Vidéo modifiée pendant l'analyse ; recopier puis réessayer"
                        )
                    state["status"] = "completed"
                except Exception as exc:
                    state.update(status="error", error=f"{type(exc).__name__}: {exc}")
                    logger.error("Échec de %s : %s", relative, exc)
                storage.write_json(state_key, state)
                results.append(state)
                print(json.dumps(state, ensure_ascii=False), flush=True)
        finally:
            del detector, classifier
            gc.collect()
            if settings.device == "cuda" and "torch" in sys.modules:
                sys.modules["torch"].cuda.empty_cache()
        return results


def watch_inbox(
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event | None = None,
) -> None:
    _weights(settings)
    stop = stop or threading.Event()
    # Les .part sont ignorés. Une taille/mtime stable réduit les lectures de copies incomplètes.
    seen: dict[Path, tuple[tuple[int, int], float]] = {}
    attempted: dict[Path, tuple[int, int]] = {}
    logger.info("Surveillance de %s ; Ctrl+C pour arrêter", settings.inbox_root)
    while not stop.is_set():
        ready = []
        current = set(input_videos(settings))
        for path in current:
            try:
                stat = path.stat()
            except OSError:
                continue
            signature = (stat.st_size, stat.st_mtime_ns)
            previous, since = seen.get(path, (signature, time.monotonic()))
            if previous != signature:
                since = time.monotonic()
            seen[path] = signature, since
            if (
                time.monotonic() - since >= settings.watch_stable_seconds
                and attempted.get(path) != signature
            ):
                ready.append(path)
        try:
            if ready:
                run_analyses(tuple(sorted(ready)), settings, classes)
                attempted.update({path: seen[path][0] for path in ready})
        except GpuBusyError:
            logger.info("GPU occupé : nouvelle tentative au prochain passage")
        seen = {path: value for path, value in seen.items() if path in current}
        attempted = {path: value for path, value in attempted.items() if path in current}
        stop.wait(settings.watch_poll_seconds)
