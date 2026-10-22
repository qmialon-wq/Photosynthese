"""Adaptateurs de la console : traitements hors HTTP, annulation coopérative."""

import hashlib
import logging
import os
import subprocess
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared import console
from shared.base_dataset import BASE_DATASET_ID
from shared.review.database import jsonb, transaction

from .classes import ClassManifest
from .config import TrainingConfig, VisionSettings
from .errors import GpuBusyError, TrainingInterrupted
from .storage import LocalStorage


def check(stop: threading.Event) -> None:
    if stop.is_set():
        raise TrainingInterrupted("Arrêt demandé ; dernier checkpoint conservé s'il existe")


def h264(source: Path, target: Path, stop: threading.Event) -> None:
    temporary = target.with_name(f".{target.stem}.encoding.mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-an",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
        try:
            while process.poll() is None:
                check(stop)
                stop.wait(0.2)
            if process.returncode:
                errors.seek(0)
                raise ValueError(
                    "Encodage navigateur impossible : " + errors.read(2000).decode(errors="replace")
                )
            check(stop)
            os.replace(temporary, target)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            temporary.unlink(missing_ok=True)


def import_video(
    row: dict[str, Any], settings: VisionSettings, classes: ClassManifest, stop: threading.Event
) -> dict[str, Any]:
    import cv2

    from .datasets.inventory import VIDEO_EXTENSIONS, file_hash, species_candidates, video_metadata

    if row["kind"] == "import_upload":
        identifier = row["request"]["upload_id"]
        with transaction() as connection:
            upload = connection.execute(
                "SELECT * FROM console_uploads WHERE id=%s", (identifier,)
            ).fetchone()
            chunks = connection.execute(
                "SELECT * FROM console_chunks WHERE upload_id=%s ORDER BY chunk_index",
                (identifier,),
            ).fetchall()
        if upload is None or upload["status"] == "cancelled":
            raise ValueError("Transfert absent ou annulé")
        key = f"inbox/{identifier}/{upload['filename']}"
        target = LocalStorage(settings.dataset_root).path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".part")
        try:
            with temporary.open("wb") as output:
                for chunk in chunks:
                    check(stop)
                    data = (
                        settings.output_root.parent
                        / "uploads"
                        / identifier
                        / str(chunk["chunk_index"])
                    ).read_bytes()
                    if hashlib.sha256(data).hexdigest() != chunk["sha256"]:
                        raise ValueError("Bloc de transfert corrompu")
                    output.write(data)
            if temporary.stat().st_size != upload["size"]:
                raise ValueError("Taille assemblée incorrecte")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        identifier = str(row["id"])
        relative = row["request"]["video"]
        key = "inbox/" + relative
        target = LocalStorage(settings.dataset_root).path(key)
    if not target.is_file() or target.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("Vidéo locale absente ou format non pris en charge")
    cap = cv2.VideoCapture(str(target))
    try:
        fps, frames, width, height = video_metadata(cap, target)
        ok, _ = cap.read()
        if not ok:
            raise ValueError("Première image vidéo illisible")
    finally:
        cap.release()
    digest = file_hash(target)
    candidates = species_candidates(target, classes)
    preview_key = f"console/previews/{identifier}.mp4"
    h264(target, LocalStorage(settings.output_root).path(preview_key), stop)
    metadata = {
        "fps": fps,
        "frames": frames,
        "width": width,
        "height": height,
        "duration_seconds": frames / fps,
        "preview_key": preview_key,
        "candidates": candidates,
        "label_source": "filename_provisional",
    }
    with transaction(write=True) as connection:
        connection.execute(
            """INSERT INTO console_videos(id,filename,video_key,sha256,species_candidate,metadata)
          VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (
                identifier,
                target.name,
                key,
                digest,
                candidates[0] if len(candidates) == 1 else None,
                jsonb(metadata),
            ),
        )
        if row["kind"] == "import_upload":
            connection.execute(
                "UPDATE console_uploads SET status='completed' WHERE id=%s", (identifier,)
            )
    return {"video_id": identifier}


def materialize(identifier: str, settings: VisionSettings, stop: threading.Event) -> Path:
    from .datasets.inventory import file_hash

    with transaction() as connection:
        dataset = connection.execute(
            "SELECT * FROM review_datasets WHERE id=%s", (identifier,)
        ).fetchone()
    if dataset is None or not dataset["archive_key"]:
        raise ValueError("Dataset non exporté")
    storage = LocalStorage(settings.output_root)
    source = storage.path(dataset["archive_key"])
    if file_hash(source) != dataset["archive_sha256"]:
        raise ValueError("Archive de dataset corrompue")
    target = storage.path(f"console/datasets/{identifier}")
    target.mkdir(parents=True, exist_ok=True)
    destination = LocalStorage(target)
    expected: dict[str, str] = {}
    for sample in dataset["manifest"]["samples"]:
        expected[f"images/{sample['crop_sha256']}.jpg"] = sample["crop_sha256"]
        expected[f"originals/{sample['original_sha256']}.jpg"] = sample["original_sha256"]
    with zipfile.ZipFile(source) as archive:
        for name in ["training.json", "manifest.json", "classes.json", *sorted(expected)]:
            check(stop)
            data = archive.read(name)
            if name in expected and hashlib.sha256(data).hexdigest() != expected[name]:
                raise ValueError("Image du dataset corrompue")
            destination.write_bytes(name, data)
    return target


def register_model(
    payload: dict[str, Any],
    actor: str,
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event | None = None,
) -> dict[str, Any]:
    import torch

    from .classification.model import create_model
    from .datasets.inventory import file_hash
    from .training.engine import SUPPORTED_MODELS

    checkpoint = LocalStorage(settings.checkpoint_root).path(payload["checkpoint_key"])
    if checkpoint.suffix == ".json":
        return register_embedding_model(payload, actor, settings, classes)
    data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    classes.check_checkpoint(data)
    if data["model_name"] not in SUPPORTED_MODELS:
        raise ValueError("Backbone du checkpoint non pris en charge")
    model = create_model(data["model_name"], classes)
    model.load_state_dict(data["state_dict"], strict=True)
    del model
    if stop:
        check(stop)
    digest = file_hash(checkpoint)
    metrics: dict[str, Any] = {}
    if "val_macro_f1" in data:
        metrics["macro_f1"] = data["val_macro_f1"]
    metadata = {
        "model_name": data["model_name"],
        "image_size": data["img_size"],
        "classes": classes.model_dump(mode="json"),
        "run_id": data.get("run_id"),
        "label_provenance": data.get("label_provenance"),
        "validation": "strict_state_dict",
        "preprocessing": data.get("preprocessing"),
        "training_config": data.get("training_config"),
    }
    identifier = str(uuid4())
    with transaction(write=True) as connection:
        if data.get("run_id"):
            events = connection.execute(
                "SELECT metrics FROM training_metrics WHERE run_id=%s", (data["run_id"],)
            ).fetchall()
            match = next(
                (
                    event["metrics"]["validation"]
                    for event in events
                    if event["metrics"]["validation"].get("macro_f1") == data.get("val_macro_f1")
                ),
                None,
            )
            if match:
                metrics["validation"] = match
        row = connection.execute(
            """INSERT INTO console_models(id,name,checkpoint_key,sha256,metadata,metrics,actor,
              family,version,dataset_version,preprocessing_version)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(sha256)
          DO UPDATE SET sha256=excluded.sha256 RETURNING id""",
            (
                identifier,
                payload["name"],
                payload["checkpoint_key"],
                digest,
                jsonb(metadata),
                jsonb(metrics),
                actor,
                "supervised" if data.get("run_id") else "existing",
                digest,
                data.get("dataset_version"),
                (data.get("preprocessing") or {}).get("version", "legacy-imagenet-resize-v1"),
            ),
        ).fetchone()
    return {"model_id": str(row["id"])}


def register_embedding_model(
    payload: dict[str, Any], actor: str, settings: VisionSettings, classes: ClassManifest
) -> dict[str, Any]:
    import json

    from .classification.contracts import ModelVersion
    from .classification.embedding_classifier import EmbeddingClassifier
    from .datasets.inventory import file_hash

    checkpoint = LocalStorage(settings.checkpoint_root).path(payload["checkpoint_key"])
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    digest = file_hash(checkpoint)
    classifier = EmbeddingClassifier(classes)
    classifier.load(
        ModelVersion(
            model_id="registration",
            version=digest,
            classifier_family="embedding",
            checkpoint=checkpoint,
            sha256=digest,
            preprocessing_version="timm-local-imagenet-v1",
        )
    )
    classifier.unload()
    metadata = {
        "model_name": data["extractor"]["architecture"],
        "image_size": data["extractor"]["profile"]["image_size"],
        "classes": classes.model_dump(mode="json"),
        "extractor": data["extractor"],
        "label_provenance": {
            "label_policy": "filename_provisional" if data["weak_validation"] else "human_only"
        },
        "validation": "embedding_integrity_and_extractor",
    }
    with transaction(write=True) as connection:
        row = connection.execute(
            """INSERT INTO console_models
          (id,name,checkpoint_key,sha256,metadata,metrics,actor,family,version,dataset_version,preprocessing_version)
          VALUES(%s,%s,%s,%s,%s,%s,%s,'embedding',%s,%s,'timm-local-imagenet-v1')
          ON CONFLICT(sha256) DO UPDATE SET sha256=excluded.sha256 RETURNING id""",
            (
                str(uuid4()),
                payload["name"],
                payload["checkpoint_key"],
                digest,
                jsonb(metadata),
                jsonb({"validation": data["selection"]["metrics"]}),
                actor,
                digest,
                data["dataset_version"],
            ),
        ).fetchone()
    return {"model_id": str(row["id"])}


def perform(
    row: dict[str, Any],
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event,
    progress: Any,
) -> dict[str, Any]:
    from .datasets.inventory import file_hash

    payload, kind = row["request"], row["kind"]
    from .classification.operations import KINDS
    from .classification.operations import perform as perform_classification

    if kind in KINDS:
        check(stop)
        result = perform_classification(
            kind, payload, settings, task_id=str(row["id"]), actor=row["actor"]
        )
        check(stop)
        return result
    check(stop)
    if kind in ("import_upload", "import_local"):
        return import_video(row, settings, classes, stop)
    if kind == "register_model":
        return register_model(payload, row["actor"], settings, classes, stop)
    if kind == "prepare_review":
        from shared.review.schemas import ImportVideo

        from .detection.megadetector import MegaDetector
        from .review.importing import prepare_import
        from .storage.gpu import exclusive_gpu

        config = settings.model_copy(deep=True)
        config.inbox_root = settings.dataset_root
        if config.detector_weights is None:
            raise ValueError("Poids MegaDetector locaux requis")
        with exclusive_gpu(config.device, config.gpu_lock_path):
            return prepare_import(
                ImportVideo(**payload),
                row,
                config,
                classes,
                MegaDetector(config.detector_weights, config),
            )
    config = settings.model_copy(deep=True)
    selected = payload.get("model")
    if selected:
        config.classifier_checkpoint = LocalStorage(settings.checkpoint_root).path(
            selected["checkpoint_key"]
        )
        if file_hash(config.classifier_checkpoint) != selected["sha256"]:
            raise ValueError("Le checkpoint enregistré a été modifié")
        from .classification.contracts import ModelVersion

        config.classifier_version = ModelVersion(
            model_id=selected["id"],
            version=selected.get("version") or selected["sha256"],
            classifier_family=selected.get("family", "existing"),
            checkpoint=config.classifier_checkpoint,
            sha256=selected["sha256"],
            preprocessing_version=selected.get(
                "preprocessing_version", "legacy-imagenet-resize-v1"
            ),
        )
    if payload.get("shadow_model"):
        from .classification.contracts import ModelVersion

        shadow = payload["shadow_model"]
        config.shadow_classifier_version = ModelVersion(
            model_id=shadow["id"],
            version=shadow.get("version") or shadow["sha256"],
            classifier_family=shadow["family"],
            checkpoint=LocalStorage(settings.checkpoint_root).path(shadow["checkpoint_key"]),
            sha256=shadow["sha256"],
            preprocessing_version=shadow["preprocessing_version"],
        )
    if kind == "analysis":
        from .commands import input_videos, run_analyses

        config.inbox_root = settings.dataset_root
        prefix = f"console/analyses/{row['id']}"
        config.output_root = settings.output_root / prefix
        config.analysis_video = payload["video_key"]
        config.analysis_force = True
        for field in (
            "detection_only",
            "detection_threshold",
            "classification_threshold",
            "infer_every_n_frames",
        ):
            setattr(config, field, payload[field])
        config.tracking.confidence_threshold = payload["track_threshold"]
        config.tracking.min_hits = payload["track_min_hits"]
        result = run_analyses(input_videos(config), config, classes, progress)[0]
        if result["status"] != "completed":
            raise ValueError(result.get("error", "Échec de l'analyse"))
        target = LocalStorage(config.output_root).path(result["output"] + "/annotated.mp4")
        progress(0, 0, "Encodage du MP4 pour le navigateur")
        h264(target, target, stop)
        result["output"] = prefix + "/" + result["output"]
        return result
    if kind not in ("training", "evaluation"):
        raise ValueError("Type de tâche inconnu")
    base_corpus = kind == "training" and payload["dataset_id"] == BASE_DATASET_ID
    if base_corpus:
        from .training.poc import prepare_snapshot

        config.train_manifest = LocalStorage(settings.output_root).path(
            f"console/datasets/base/{row['id']}/training.json"
        )
        progress(0, 0, "Préparation du corpus de base et des corrections humaines")
        check(stop)
        prepare_snapshot(config)
        check(stop)
    else:
        root = materialize(payload["dataset_id"], settings, stop)
        config.train_manifest = root / "training.json"
        config.output_root = root
    if kind == "evaluation":
        from .training.commands import evaluate_classifier

        return {
            "metrics": evaluate_classifier(config, classes, payload["split"]),
            "model_id": selected["id"],
        }
    from .commands import train_from_manifest

    config.training = TrainingConfig(
        **{k: v for k, v in payload.items() if k != "dataset_id"},
        run_id=str(row["id"]),
        allow_filename_labels=base_corpus,
        database_metrics=True,
    )
    last = settings.checkpoint_root / str(row["id"]) / "last.pt"
    if last.is_file():
        config.training.resume_checkpoint = last
    result = train_from_manifest(config, classes, stop)
    result.update(
        register_model(
            {
                "checkpoint_key": f"{row['id']}/best.pt",
                "name": f"{config.training.model_name} · {str(row['id'])[:8]}",
            },
            row["actor"],
            settings,
            classes,
        )
    )
    return result


class TaskLog(logging.Handler):
    def __init__(self, identifier: str):
        super().__init__(logging.INFO)
        self.identifier = identifier

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.INFO:
            return
        try:
            with transaction() as connection:
                console.log(connection, self.identifier, record.getMessage())
        except Exception:
            pass  # Un échec de journalisation ne doit pas masquer l'erreur de calcul.


def execute(
    identifier: str,
    settings: VisionSettings,
    classes: ClassManifest,
    shutdown: threading.Event | None = None,
) -> dict[str, Any]:
    local_stop, done = threading.Event(), threading.Event()
    last_update = 0.0

    def progress(current: int, total: int, stage: str = "Analyse des images") -> None:
        nonlocal last_update
        check(local_stop)
        if time.monotonic() - last_update < 1:
            return
        with transaction() as connection:
            connection.execute(
                "UPDATE console_tasks SET progress=%s WHERE id=%s",
                (jsonb({"current": current, "total": total, "stage": stage}), identifier),
            )
        last_update = time.monotonic()

    def monitor() -> None:
        while not done.is_set():
            try:
                if console.task(identifier)["cancel_requested"] or (shutdown and shutdown.is_set()):
                    local_stop.set()
            except Exception:
                pass
            done.wait(0.5)

    with transaction() as session:
        session.execute("SELECT pg_advisory_lock(hashtextextended(%s,1))", (identifier,))
        session.commit()
        listener = threading.Thread(target=monitor, daemon=True)
        handler = TaskLog(identifier)
        try:
            row = console.task(identifier)
            if row["status"] in ("completed", "cancelled", "error"):
                return {"status": "completed", "task_id": identifier}
            if row["cancel_requested"]:
                local_stop.set()
            listener.start()
            logging.getLogger().addHandler(handler)
            with transaction(write=True) as connection:
                connection.execute(
                    "UPDATE console_tasks SET status='running' WHERE id=%s", (identifier,)
                )
                console.log(connection, identifier, "Traitement démarré sur le worker local")
            try:
                result = perform(row, settings, classes, local_stop, progress)
                check(local_stop)
                status, error = "completed", None
            except GpuBusyError:
                with transaction() as connection:
                    connection.execute(
                        "UPDATE console_tasks SET status='queued' WHERE id=%s", (identifier,)
                    )
                raise
            except TrainingInterrupted as exc:
                if not console.task(identifier)["cancel_requested"]:
                    with transaction() as connection:
                        connection.execute(
                            "UPDATE console_tasks SET status='queued' WHERE id=%s", (identifier,)
                        )
                    raise
                result, status, error = None, "cancelled", str(exc)
            except Exception as exc:
                result, status, error = None, "error", f"{type(exc).__name__}: {exc}"
            with transaction(write=True) as connection:
                connection.execute(
                    "UPDATE console_tasks SET status=%s,result=%s,error=%s,finished_at=now() "
                    "WHERE id=%s",
                    (status, jsonb(result), error, identifier),
                )
                console.log(connection, identifier, error or "Traitement terminé")
            return {"status": "completed", "task_id": identifier}
        finally:
            done.set()
            if listener.is_alive():
                listener.join(timeout=4)
            logging.getLogger().removeHandler(handler)
            session.execute("SELECT pg_advisory_unlock(hashtextextended(%s,1))", (identifier,))
