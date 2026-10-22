"""Soumissions asynchrones pour la classification alternative."""

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.review import Actor
from shared import console
from shared.classification_jobs import (
    Clustering,
    Comparison,
    DatasetPreparation,
    EmbeddingTraining,
    Extract,
    Promotion,
    Rollback,
    freeze_comparison,
)
from shared.review.database import ReviewError, transaction

router = APIRouter(prefix="/classification", tags=["classification"])


@router.post("/datasets/prepare", status_code=202)
def prepare(body: DatasetPreparation, actor: Actor) -> dict[str, Any]:
    return console.submit("classification_dataset", body.model_dump(), actor)


@router.get("/weights")
def weights() -> list[dict[str, Any]]:
    root = Path(os.getenv("STORAGE_ROOT", "/storage")) / "models/pretrained"
    return [
        {
            "architecture": architecture,
            "available": (root / architecture / "manifest.json").is_file(),
        }
        for architecture in (
            "tf_efficientnetv2_b0",
            "efficientnetv2_s",
            "convnext_tiny",
            "resnet50",
        )
    ]


@router.post("/embeddings/extract", status_code=202)
def extract(body: Extract, actor: Actor) -> dict[str, Any]:
    return console.submit("embeddings_extract", body.model_dump(), actor)


@router.post("/embeddings/train", status_code=202)
def train(body: EmbeddingTraining, actor: Actor) -> dict[str, Any]:
    return console.submit(
        "embeddings_train", {**body.model_dump(), "output_key": f"embeddings/{uuid4()}"}, actor
    )


@router.post("/clustering", status_code=202)
def cluster(body: Clustering, actor: Actor) -> dict[str, Any]:
    return console.submit(
        "embeddings_cluster",
        {**body.model_dump(), "output_key": f"exploration/{uuid4()}.json"},
        actor,
    )


@router.post("/comparisons", status_code=202)
def compare(body: Comparison, actor: Actor) -> dict[str, Any]:
    return console.submit("classifiers_compare", freeze_comparison(body), actor)


@router.get("/comparisons")
def comparisons(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            """SELECT id,created_at,report->>'dataset_version' AS dataset_version,
            report->'protocol' AS protocol,report->'human_validated' AS human_validated,
            (SELECT jsonb_agg(m - 'predictions')
             FROM jsonb_array_elements(report->'models') AS m) AS models
            FROM classifier_comparisons ORDER BY created_at DESC LIMIT %s""",
            (limit,),
        ).fetchall()


@router.get("/comparisons/{identifier}")
def comparison(identifier: UUID) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM classifier_comparisons WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Comparaison introuvable", 404)
    return row


@router.post("/models/{identifier}/promote", status_code=202)
def promote(identifier: UUID, body: Promotion, actor: Actor) -> dict[str, Any]:
    return console.submit(
        "model_promote", {"candidate_id": str(identifier), **body.model_dump(mode="json")}, actor
    )


@router.post("/models/{identifier}/rollback", status_code=202)
def rollback(identifier: UUID, body: Rollback, actor: Actor) -> dict[str, Any]:
    return console.submit(
        "model_rollback", {"model_id": str(identifier), "reason": body.reason}, actor
    )


@router.get("/models/{identifier}/history")
def history(identifier: UUID) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            """SELECT * FROM model_promotions WHERE model_id=%s OR previous_model_id=%s
            ORDER BY created_at DESC""",
            (identifier, identifier),
        ).fetchall()


@router.get("/models/{identifier}")
def model(identifier: UUID) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM console_models WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Modèle introuvable", 404)
    return row


@router.post("/models/{identifier}/archive")
def archive(identifier: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(write=True) as connection:
        row = connection.execute(
            "UPDATE console_models SET status='archived' WHERE id=%s AND NOT active RETURNING id",
            (identifier,),
        ).fetchone()
    if row is None:
        raise ReviewError("Modèle absent ou encore actif")
    return {"id": identifier, "status": "archived", "actor": actor}


@router.get("/tasks/{identifier}/artifact", response_class=FileResponse)
def artifact(identifier: UUID) -> FileResponse:
    row = console.task(str(identifier))
    fields = {
        "classification_dataset": "manifest",
        "embeddings_extract": "index",
        "embeddings_cluster": "report",
        "classifiers_compare": "report_key",
    }
    field = fields.get(row["kind"])
    if row["status"] != "completed" or field is None:
        raise ReviewError("Export JSON indisponible", 404)
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/vision").resolve()
    path = (root / row["result"][field]).resolve()
    if not path.is_relative_to(root) or path.suffix != ".json" or not path.is_file():
        raise ReviewError("Export JSON absent du stockage de résultats", 404)
    return FileResponse(path, media_type="application/json", filename=path.name)
