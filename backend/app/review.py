import os
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from shared.review import service
from shared.review.database import ReviewError, transaction
from shared.review.schemas import (
    BatchDecision,
    DatasetRequest,
    Decision,
    ImportVideo,
    Operation,
    State,
)

router = APIRouter(prefix="/review", tags=["human-review"])


def reviewer(request: Request) -> str:
    return request.state.user["id"]


Actor = Annotated[str, Depends(reviewer)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


def stored_file(key: str | None, download_name: str | None = None) -> FileResponse:
    if key is None:
        raise ReviewError("Artefact en attente", 409)
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/vision").resolve()
    target = (root / key).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ReviewError("Artefact absent", 404)
    return FileResponse(target, filename=download_name)


@router.post("/videos/import", status_code=202, response_model=Operation)
def import_video(body: ImportVideo, actor: Actor) -> dict[str, Any]:
    # Le décodage, la copie, le hash et la détection appartiennent au worker.
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "datasets/inbox").resolve()
    path = (root / body.video).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".m4v",
    }:
        raise HTTPException(422, "Vidéo hors inbox ou extension invalide")
    if not path.is_file():
        raise HTTPException(404, "Déposer la vidéo dans data/datasets/inbox")
    return service.submit("import_video", body.model_dump(), actor)


@router.get("/operations/{identifier}")
def operation_status(identifier: UUID) -> dict[str, Any]:
    return service.get_operation(str(identifier))


@router.get("/species")
def species() -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute("SELECT * FROM review_species ORDER BY class_index").fetchall()


@router.get("/videos")
def videos(
    status: Literal["processing", "ready", "no_detections", "error"] | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[dict[str, Any]]:
    return service.list_videos(status, limit, offset)


@router.get("/videos/{identifier}/imports")
def imports(identifier: str) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM review_imports WHERE video_id=%s ORDER BY created_at", (identifier,)
        ).fetchall()


@router.get("/samples")
def samples(
    state: State | None = None,
    label: str | None = None,
    quality: Literal["blurry", "too_small", "near_duplicate"] | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
    video_id: str | None = None,
) -> list[dict[str, Any]]:
    return service.list_samples(state, label, quality, limit, offset, video_id)


@router.get("/samples/{identifier}")
def sample(identifier: str) -> dict[str, Any]:
    return service.get_sample(identifier)


@router.post("/samples/{identifier}/decisions")
def decision(identifier: str, body: Decision, actor: Actor) -> dict[str, Any]:
    return service.decide(identifier, body, actor)


@router.post("/samples/batch-decisions")
def batch_decisions(body: BatchDecision, actor: Actor) -> list[dict[str, Any]]:
    return service.decide_batch(body, actor)


@router.get("/samples/{identifier}/history")
def history(identifier: str) -> list[dict[str, Any]]:
    return service.history(identifier)


@router.get("/samples/{identifier}/images/{kind}")
def image(
    identifier: str,
    kind: Literal["original", "initial_crop", "crop"],
    revision: Annotated[int | None, Query(ge=0)] = None,
) -> FileResponse:
    row = service.get_sample(identifier)
    key = row[
        {"original": "original_image_key", "initial_crop": "original_crop_key", "crop": "crop_key"}[
            kind
        ]
    ]
    if revision is not None and kind == "crop":
        with transaction() as connection:
            previous = connection.execute(
                "SELECT crop_key FROM review_revisions WHERE sample_id=%s AND revision=%s",
                (identifier, revision),
            ).fetchone()
        if previous is None:
            raise ReviewError("Révision inconnue", 404)
        key = previous["crop_key"]
    return stored_file(key)


@router.post("/datasets", status_code=202, response_model=Operation)
def export_dataset(body: DatasetRequest, actor: Actor) -> dict[str, Any]:
    return service.submit("export_dataset", body.model_dump(), actor)


@router.get("/datasets")
def datasets(limit: Limit = 50, offset: Offset = 0) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            (
                "SELECT id,name,actor,created_at,archive_sha256 FROM review_datasets ORDER BY "
                "created_at DESC LIMIT %s OFFSET %s"
            ),
            (limit, offset),
        ).fetchall()


@router.get("/datasets/{identifier}")
def dataset(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM review_datasets WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Dataset inconnu", 404)
    return row


@router.post("/datasets/{identifier}/rebuild", status_code=202, response_model=Operation)
def rebuild(identifier: str, actor: Actor) -> dict[str, Any]:
    dataset(identifier)
    return service.submit("rebuild_export", {"dataset_id": identifier}, actor)


@router.get("/datasets/{identifier}/archive")
def download(identifier: str) -> FileResponse:
    row = dataset(identifier)
    return stored_file(row["archive_key"], f"{row['name']}-{identifier[:12]}.zip")
