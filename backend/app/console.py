import hashlib
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi import Path as PathParameter
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.review import Actor, stored_file
from shared import console
from shared.base_dataset import BASE_DATASET_ID, describe_base_dataset
from shared.review.database import ReviewError, transaction
from shared.review.schemas import Operation
from shared.vision_jobs import AnalysisRequest

router = APIRouter(prefix="/console", tags=["web-console"])
CHUNK_SIZE = 4 * 1024 * 1024
EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


def storage() -> Path:
    return Path(os.getenv("STORAGE_ROOT", "/storage")).resolve()


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Upload(Body):
    filename: str = Field(min_length=1, max_length=200)
    size: int = Field(gt=0, le=20 * 1024**3)

    @field_validator("filename")
    @classmethod
    def safe_name(cls, value: str) -> str:
        if any(c in value for c in "/\\\x00:") or Path(value).suffix.lower() not in EXTENSIONS:
            raise ValueError("Nom de fichier vidéo invalide")
        return value


class LocalVideo(Body):
    video: str

    @field_validator("video")
    @classmethod
    def relative(cls, value: str) -> str:
        return AnalysisRequest(video=value).video


class Analysis(Body):
    detection_only: bool = False
    detection_threshold: float = Field(default=0.1, ge=0.005, le=1)
    classification_threshold: float = Field(default=0.48, ge=0, le=1)
    track_threshold: float = Field(default=0.6, ge=0, le=1)
    track_min_hits: int = Field(default=2, ge=1, le=100)
    infer_every_n_frames: int = Field(default=2, ge=1, le=1000)


class Training(Body):
    dataset_id: str = Field(pattern=r"^(base|[a-f0-9]{64})$")
    model_name: Literal["convnext_tiny", "tf_efficientnetv2_b0", "efficientnetv2_s", "resnet50"] = (
        "tf_efficientnetv2_b0"
    )
    batch_size: int = Field(default=2, ge=1, le=64)
    accumulation_steps: int = Field(default=4, ge=1, le=64)
    image_size: int = Field(default=224, ge=32, le=512)
    epochs_head: int = Field(default=6, ge=1, le=200)
    epochs_finetune: int = Field(default=18, ge=1, le=500)
    patience: int = Field(default=6, ge=1, le=100)
    amp: Literal["auto", "off"] = "auto"
    initialization: Literal["pretrained", "scratch"] = "pretrained"


class ModelRegistration(Body):
    name: str = Field(min_length=1, max_length=100)
    checkpoint_key: str = Field(min_length=1, max_length=250)

    @field_validator("checkpoint_key")
    @classmethod
    def relative(cls, value: str) -> str:
        AnalysisRequest(video=value)
        if Path(value).suffix != ".pt":
            raise ValueError("Checkpoint .pt local requis")
        return value


class Evaluation(Body):
    dataset_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    split: Literal["val", "test"] = "test"


def dataset_ready(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM review_datasets WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None or row["archive_sha256"] is None:
        raise ReviewError("Version de dataset absente ou export non terminé", 422)
    return row


@router.get("/dashboard")
def dashboard() -> dict[str, Any]:
    with transaction() as connection:
        counts = connection.execute(
            """SELECT
          (SELECT count(DISTINCT sha256) FROM ("""
            + console.VIDEO_QUERY
            + """) v) videos,
          (SELECT count(DISTINCT label) FROM review_revisions r JOIN review_samples s
           ON s.id=r.sample_id AND s.current_revision=r.revision
           WHERE r.state IN ('validated','corrected')) species,
          (SELECT count(*) FROM review_samples s JOIN review_revisions r
           ON s.id=r.sample_id AND s.current_revision=r.revision WHERE r.state='pending') pending,
          (SELECT count(*) FROM console_tasks WHERE status IN ('running','queued')) tasks
        """
        ).fetchone()
        distribution = connection.execute("""SELECT r.label,count(*) count FROM review_revisions r
          JOIN review_samples s ON s.id=r.sample_id AND s.current_revision=r.revision
          WHERE r.state IN ('validated','corrected')
          GROUP BY r.label ORDER BY count DESC""").fetchall()
        latest = connection.execute(
            "SELECT metadata FROM training_runs ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return {
        "counts": counts,
        "distribution": distribution,
        "latest_training": latest["metadata"] if latest else None,
    }


@router.post("/uploads", status_code=201)
def create_upload(body: Upload, actor: Actor) -> dict[str, Any]:
    identifier = str(uuid4())
    with transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO console_uploads(id,filename,size,actor) VALUES(%s,%s,%s,%s)",
            (identifier, body.filename, body.size, actor),
        )
    return {"id": identifier, "chunk_size": CHUNK_SIZE}


def write_chunk(identifier: str, index: int, data: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(data).hexdigest()
    with transaction(write=True) as connection:
        row = connection.execute(
            "SELECT * FROM console_uploads WHERE id=%s FOR UPDATE", (identifier,)
        ).fetchone()
        if row is None or row["status"] != "uploading":
            raise ReviewError("Transfert absent ou fermé", 409)
        expected = min(CHUNK_SIZE, row["size"] - index * CHUNK_SIZE)
        if expected <= 0 or len(data) != expected:
            raise ReviewError("Taille de bloc invalide", 422)
        previous = connection.execute(
            "SELECT sha256 FROM console_chunks WHERE upload_id=%s AND chunk_index=%s",
            (identifier, index),
        ).fetchone()
        if previous and previous["sha256"] != digest:
            raise ReviewError("Bloc déjà reçu avec un contenu différent")
        target = storage() / "results/uploads" / identifier / str(index)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".part")
        temporary.write_bytes(data)
        os.replace(temporary, target)
        connection.execute(
            "INSERT INTO console_chunks VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (identifier, index, len(data), digest),
        )
    return {"index": index, "size": len(data)}


@router.put("/uploads/{identifier}/chunks/{index}")
async def upload_chunk(
    identifier: UUID, index: Annotated[int, PathParameter(ge=0)], request: Request, actor: Actor
) -> dict[str, Any]:
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > CHUNK_SIZE:
            raise HTTPException(413, "Bloc trop volumineux")
    return await run_in_threadpool(write_chunk, str(identifier), index, bytes(data))


@router.post("/uploads/{identifier}/complete", status_code=202, response_model=Operation)
def complete_upload(identifier: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(write=True) as connection:
        row = connection.execute(
            "SELECT * FROM console_uploads WHERE id=%s FOR UPDATE", (identifier,)
        ).fetchone()
        size = connection.execute(
            "SELECT coalesce(sum(size),0) size FROM console_chunks WHERE upload_id=%s",
            (identifier,),
        ).fetchone()["size"]
        if row is None or row["status"] != "uploading" or size != row["size"]:
            raise ReviewError("Transfert incomplet ou fermé")
        connection.execute("UPDATE console_uploads SET status='queued' WHERE id=%s", (identifier,))
        return console.submit("import_upload", {"upload_id": str(identifier)}, actor, connection)


@router.delete("/uploads/{identifier}", status_code=204)
def cancel_upload(identifier: UUID, actor: Actor) -> None:
    with transaction(write=True) as connection:
        connection.execute(
            "UPDATE console_uploads SET status='cancelled' WHERE id=%s AND status='uploading'",
            (identifier,),
        )


@router.post("/videos/local", status_code=202, response_model=Operation)
def local_video(body: LocalVideo, actor: Actor) -> dict[str, Any]:
    return console.submit("import_local", body.model_dump(), actor)


@router.get("/videos")
def videos(
    q: str = "",
    species: str = "",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Literal["ready", "processing", "no_detections", "error"] | None = None,
) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM ("
            + console.VIDEO_QUERY
            + """) v
          WHERE filename ILIKE %s AND (%s='' OR species_candidate=%s)
          AND (%s::text IS NULL OR status=%s)
          ORDER BY created_at DESC,id LIMIT %s OFFSET %s""",
            (f"%{q}%", species, species, status, status, limit, offset),
        ).fetchall()


@router.get("/videos/{identifier}")
def read_video(identifier: str) -> dict[str, Any]:
    return console.video(identifier)


@router.get("/videos/{identifier}/file")
def video_file(identifier: str) -> FileResponse:
    row = console.video(identifier)
    if row["metadata"].get("preview_key"):
        return stored_file(row["metadata"]["preview_key"])
    root = (storage() / "datasets").resolve()
    target = (root / row["video_key"]).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ReviewError("Vidéo source absente", 404)
    return FileResponse(target, media_type="video/mp4" if target.suffix.lower() == ".mp4" else None)


@router.post("/videos/{identifier}/analyze", status_code=202, response_model=Operation)
def analyze(identifier: str, body: Analysis, actor: Actor) -> dict[str, Any]:
    video = console.video(identifier)
    payload = {"video_key": video["video_key"], "video_id": identifier, **body.model_dump()}
    if not body.detection_only:
        with transaction() as connection:
            model = connection.execute(
                "SELECT id,checkpoint_key,sha256 FROM console_models WHERE active"
            ).fetchone()
        if model is None:
            raise ReviewError("Enregistrer et activer un modèle, ou choisir Détection seule", 422)
        payload["model"] = {**model, "id": str(model["id"])}
    return console.submit("analysis", payload, actor)


@router.post("/videos/{identifier}/prepare-review", status_code=202, response_model=Operation)
def prepare_review(identifier: str, actor: Actor) -> dict[str, Any]:
    row = console.video(identifier)
    return console.submit("prepare_review", {"video": row["video_key"]}, actor)


@router.get("/tasks")
def tasks(kind: str | None = None, limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM console_tasks WHERE (%s::text IS NULL OR kind=%s) "
            "ORDER BY created_at DESC LIMIT %s",
            (kind, kind, limit),
        ).fetchall()


@router.get("/tasks/{identifier}")
def task(identifier: UUID) -> dict[str, Any]:
    row = console.task(str(identifier))
    if row["kind"] == "training":
        with transaction() as connection:
            run = connection.execute(
                "SELECT metadata FROM training_runs WHERE run_id=%s", (str(identifier),)
            ).fetchone()
        if run and run["metadata"].get("phase"):
            metadata = run["metadata"]
            row["progress"] = {
                "stage": metadata["phase"],
                "current": metadata["epoch"],
                "total": row["request"][
                    "epochs_head" if metadata["phase"] == "head" else "epochs_finetune"
                ],
            }
    return row


@router.post("/tasks/{identifier}/cancel", status_code=202)
def cancel_task(identifier: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(write=True) as connection:
        row = connection.execute(
            "SELECT * FROM console_tasks WHERE id=%s FOR UPDATE", (identifier,)
        ).fetchone()
        if row is None or row["status"] not in ("queued", "running"):
            raise ReviewError("Cette tâche n'est plus active")
        connection.execute(
            "UPDATE console_tasks SET cancel_requested=true WHERE id=%s", (identifier,)
        )
        console.log(connection, str(identifier), f"Arrêt demandé par {actor}")
    return {"id": str(identifier), "cancel_requested": True}


@router.get("/tasks/{identifier}/logs")
def logs(identifier: UUID, after: int = Query(0, ge=0)) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM (SELECT * FROM console_logs WHERE task_id=%s AND id>%s "
            "ORDER BY id DESC LIMIT 500) recent ORDER BY id",
            (identifier, after),
        ).fetchall()


@router.get("/tasks/{identifier}/artifacts/{artifact}")
def artifact(identifier: UUID, artifact: Literal["video", "report", "statistics"]) -> FileResponse:
    row = console.task(str(identifier))
    if row["kind"] != "analysis" or row["status"] != "completed":
        raise ReviewError("Analyse non terminée")
    names = {"video": "annotated.mp4", "report": "report.json", "statistics": "statistics.json"}
    return stored_file(f"{row['result']['output']}/{names[artifact]}")


@router.get("/training/datasets")
def training_datasets() -> list[dict[str, Any]]:
    with transaction() as connection:
        versions = connection.execute(
            "SELECT id,name,archive_sha256 FROM review_datasets ORDER BY created_at DESC"
        ).fetchall()
    return [
        describe_base_dataset(storage() / "results/vision"),
        *[
            {
                "id": row["id"],
                "name": row["name"],
                "source": "review",
                "ready": row["archive_sha256"] is not None,
                "unavailable_reason": None if row["archive_sha256"] else "Export en cours",
            }
            for row in versions
        ],
    ]


@router.post("/training", status_code=202, response_model=Operation)
def train(body: Training, actor: Actor) -> dict[str, Any]:
    if body.dataset_id == BASE_DATASET_ID:
        base = describe_base_dataset(storage() / "results/vision")
        if not base["ready"]:
            raise ReviewError(base["unavailable_reason"], 422)
        return console.submit("training", body.model_dump(), actor)
    dataset = dataset_ready(body.dataset_id)
    samples = dataset["manifest"]["samples"]
    train_labels = {row["label"] for row in samples if row["split"] == "train"}
    labels = {row["name"] for row in dataset["manifest"]["classes"]["classes"]}
    if (
        not train_labels
        or not train_labels.issubset(labels)
        or not any(row["split"] == "val" for row in samples)
    ):
        raise ReviewError(
            "Le dataset doit avoir les 10 classes validées dans train et un split val non vide", 422
        )
    return console.submit("training", body.model_dump(), actor)


@router.get("/models")
def models() -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM console_models ORDER BY created_at DESC"
        ).fetchall()


@router.post("/models", status_code=202, response_model=Operation)
def register_model(body: ModelRegistration, actor: Actor) -> dict[str, Any]:
    return console.submit("register_model", body.model_dump(), actor)


@router.post("/models/{identifier}/activate")
def activate(identifier: UUID, actor: Actor) -> dict[str, Any]:
    return console.activate_model(str(identifier))


@router.post("/models/{identifier}/evaluate", status_code=202, response_model=Operation)
def evaluate(identifier: UUID, body: Evaluation, actor: Actor) -> dict[str, Any]:
    dataset_ready(body.dataset_id)
    with transaction() as connection:
        row = connection.execute(
            "SELECT id,checkpoint_key,sha256 FROM console_models WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Modèle inconnu", 404)
    return console.submit(
        "evaluation", {**body.model_dump(), "model": {**row, "id": str(row["id"])}}, actor
    )
