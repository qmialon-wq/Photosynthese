"""Soumissions asynchrones pour la classification alternative."""

import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter

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
    if len(set(body.model_ids)) != len(body.model_ids):
        raise ReviewError("Sélectionner des modèles distincts", 422)
    if body.split == "test" and (not body.confirm_final_test or body.allow_weak_labels):
        raise ReviewError(
            "Test final : confirmation explicite et annotations humaines requises", 422
        )
    with transaction() as connection:
        rows = connection.execute(
            "SELECT * FROM console_models WHERE id=ANY(%s)", (body.model_ids,)
        ).fetchall()
    if len(rows) != len(body.model_ids) or any(r["status"] == "archived" for r in rows):
        raise ReviewError("Modèle absent ou archivé", 422)
    if body.split == "test" and any(r["status"] not in ("active", "validated") for r in rows):
        raise ReviewError(
            "Réserver le test final aux modèles déjà sélectionnés sur validation", 422
        )
    payload = body.model_dump(mode="json", exclude={"model_ids", "confirm_final_test"})
    payload["models"] = [
        {
            "model_id": str(r["id"]),
            "version": r["version"] or str(r["id"]),
            "classifier_family": r["family"],
            "checkpoint": r["checkpoint_key"],
            "sha256": r["sha256"],
            "preprocessing_version": r["preprocessing_version"],
        }
        for r in rows
    ]
    return console.submit("classifiers_compare", payload, actor)


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
