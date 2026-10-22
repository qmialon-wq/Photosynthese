"""Opérations exécutées dans le consommateur vision existant."""

from typing import Any

from ..config import VisionSettings
from ..storage import LocalStorage

KINDS = {"embeddings_extract", "embeddings_train"}


def perform(kind: str, payload: dict[str, Any], settings: VisionSettings) -> dict[str, Any]:
    results = LocalStorage(settings.output_root)
    architecture = payload.get("architecture", "tf_efficientnetv2_b0")
    from .pretrained import PRETRAINED_MODELS

    if architecture not in PRETRAINED_MODELS:
        raise ValueError("Architecture généraliste inconnue")
    pretrained = (
        settings.checkpoint_root.parent / "models/pretrained" / architecture / "manifest.json"
    )
    if kind == "embeddings_extract":
        from .embeddings import extract_embeddings

        return extract_embeddings(
            results.path(payload["manifest_key"]),
            results.path(payload.get("storage_key", "")),
            results.path("embeddings"),
            pretrained,
            device=settings.device,
            image_size=payload.get("image_size", 224),
            batch_size=payload.get("batch_size", 2),
            allow_weak_labels=payload.get("allow_weak_labels", False),
            lock=settings.gpu_lock_path,
        )
    if kind == "embeddings_train":
        from ..training.embedding import train_embedding_classifier

        return train_embedding_classifier(
            results.path(payload["index_key"]),
            LocalStorage(settings.checkpoint_root).path(payload["output_key"]),
            pretrained,
            candidates=tuple(payload.get("candidates", ["logistic", "knn", "linear_svm"])),
            seed=payload.get("seed", 42),
            allow_weak_validation=payload.get("allow_weak_validation", False),
        )
    raise ValueError(f"Opération de classification inconnue : {kind}")
