import hashlib
from typing import Any

from shared.review.database import jsonb, transaction
from shared.review.schemas import DatasetRequest, ImportVideo

from ..classes import ClassManifest
from ..config import VisionSettings
from ..errors import GpuBusyError
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from .exporting import archive, snapshot
from .images import render
from .importing import prepare_import


def render_revision(payload: dict[str, Any], storage: LocalStorage) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            """SELECT r.*,f.image_key,f.sha256 FROM review_revisions r JOIN review_samples s ON
        s.id=r.sample_id
          JOIN review_frames f ON f.id=s.frame_id WHERE r.sample_id=%s AND r.revision=%s""",
            (payload["sample_id"], payload["revision"]),
        ).fetchone()
    if row is None:
        raise ValueError("Révision absente")
    if row["crop_key"]:
        return {"sample_id": row["sample_id"], "revision": row["revision"]}
    if hashlib.sha256(storage.read_bytes(row["image_key"])).hexdigest() != row["sha256"]:
        raise ValueError("Image originale corrompue")
    result = render(storage, row["image_key"], row["box"], row["recipe"])
    with transaction(write=True) as connection:
        connection.execute(
            """UPDATE review_revisions SET crop_key=%s,crop_sha256=%s,quality=%s,
            render_status='ready'
          WHERE sample_id=%s AND revision=%s""",
            (
                result["crop_key"],
                result["crop_sha256"],
                jsonb(result["quality"]),
                row["sample_id"],
                row["revision"],
            ),
        )
    return {"sample_id": row["sample_id"], "revision": row["revision"]}


def perform(
    row: dict[str, Any], settings: VisionSettings, classes: ClassManifest
) -> dict[str, Any]:
    storage = LocalStorage(settings.output_root)
    if row["kind"] == "render_crop":
        return render_revision(row["payload"], storage)
    if row["kind"] == "export_dataset":
        # Conserver l'identifiant du snapshot si l'écriture du ZIP est interrompue.
        identifier = (row.get("result") or {}).get("dataset_id")
        if identifier is None:
            identifier = snapshot(DatasetRequest(**row["payload"]), row["actor"], classes)
            with transaction(write=True) as connection:
                connection.execute(
                    "UPDATE review_operations SET result=%s WHERE id=%s",
                    (jsonb({"dataset_id": identifier}), row["id"]),
                )
        return archive(identifier, storage)
    if row["kind"] == "rebuild_export":
        return archive(row["payload"]["dataset_id"], storage)
    if row["kind"] != "import_video":
        raise ValueError("Opération de revue inconnue")
    from ..classification.model import TorchClassifier
    from ..detection.megadetector import MegaDetector

    request = ImportVideo(**row["payload"])
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        if settings.detector_weights is None:
            raise ValueError("Poids MegaDetector locaux requis ; lancer make detector-fetch")
        detector = MegaDetector(settings.detector_weights, settings)
        classifier = None
        if request.classify:
            if settings.classifier_checkpoint is None:
                raise ValueError("Checkpoint classificateur local requis")
            classifier = TorchClassifier(
                settings.classifier_checkpoint,
                classes,
                device=settings.device,
                threshold=settings.classification_threshold,
            )
        return prepare_import(request, row, settings, classes, detector, classifier)


def execute_operation(
    identifier: str, settings: VisionSettings, classes: ClassManifest
) -> dict[str, Any]:
    # Verrou de session distinct du verrou court de mutation : résiste aux doublons Redis.
    with transaction() as session:
        session.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (identifier,))
        session.commit()
        try:
            with transaction(write=True) as connection:
                row = connection.execute(
                    "SELECT * FROM review_operations WHERE id=%s", (identifier,)
                ).fetchone()
                if row is None:
                    raise ValueError("Opération inconnue")
                if row["status"] == "completed":
                    return {"status": "completed", **row["result"]}
                if row["status"] == "error":
                    raise ValueError(row["error"])
                connection.execute(
                    "UPDATE review_operations SET status='running' WHERE id=%s", (identifier,)
                )
            try:
                result = perform(row, settings, classes)
            except GpuBusyError:
                with transaction(write=True) as connection:
                    connection.execute(
                        "UPDATE review_operations SET status='queued' WHERE id=%s", (identifier,)
                    )
                raise
            except Exception as exc:
                with transaction(write=True) as connection:
                    if row["kind"] == "import_video":
                        connection.execute(
                            """UPDATE review_videos SET status='error',diagnostics=%s WHERE id IN
                            (SELECT video_id FROM review_imports WHERE id=%s) AND
        status='processing'""",
                            (jsonb({"error": str(exc)}), identifier),
                        )
                    if row["kind"] == "render_crop":
                        connection.execute(
                            """UPDATE review_revisions SET render_status='error'
                            WHERE sample_id=%s AND revision=%s AND crop_key IS NULL""",
                            (row["payload"]["sample_id"], row["payload"]["revision"]),
                        )
                    connection.execute(
                        "UPDATE review_operations SET status='error',error=%s,finished_at=now() "
                        "WHERE id=%s",
                        (f"{type(exc).__name__}: {exc}", identifier),
                    )
                raise
            with transaction(write=True) as connection:
                connection.execute(
                    (
                        "UPDATE review_operations SET status='completed',result=%s,"
                        "finished_at=now() "
                        "WHERE id=%s"
                    ),
                    (jsonb(result), identifier),
                )
            return {"status": "completed", **result}
        finally:
            session.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (identifier,))
