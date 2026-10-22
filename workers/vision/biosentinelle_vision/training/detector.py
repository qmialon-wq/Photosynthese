"""Contrat indépendant du classificateur ; aucun backend de fine-tuning supposé."""

from pathlib import Path
from typing import Any, Literal, Protocol

from PIL import Image
from pydantic import BaseModel, ConfigDict

from ..datasets.inventory import file_hash
from ..errors import ManifestError, ModelError
from ..schemas import Box
from ..storage import LocalStorage


class DetectorTrainingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = "md_v5a.0.0"
    backend: str = "unconfigured"
    training_format: Literal["normalized_boxes_v1"] = "normalized_boxes_v1"
    annotations: Path
    image_root: Path
    weights: Path | None = None


class AnnotatedImage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_key: str
    sha256: str
    video_id: str
    split: Literal["train", "val", "test"]
    human_verified: Literal[True]
    boxes: tuple[Box, ...]


class BoxDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["normalized_boxes_v1"]
    target: Literal["animal"]
    images: tuple[AnnotatedImage, ...]


class DetectorTrainer(Protocol):
    def check_compatibility(self, config: DetectorTrainingConfig) -> None:
        """Vérifier modèle, poids, catégories de sortie et conversion du format."""
        ...

    def train(self, config: DetectorTrainingConfig, dataset: BoxDataset) -> Path: ...


def validate_detector_dataset(config: DetectorTrainingConfig) -> dict[str, Any]:
    source = BoxDataset.model_validate_json(config.annotations.read_text(encoding="utf-8"))
    if not source.images or not any(row.boxes for row in source.images if row.split == "train"):
        raise ManifestError("Au moins une bounding box humaine en train est requise")
    if not any(row.split == "val" for row in source.images):
        raise ManifestError("Ensemble val de bounding boxes absent")
    storage = LocalStorage(config.image_root)
    groups: dict[str, str] = {}
    hashes: dict[str, str] = {}
    keys = set()
    for row in source.images:
        if row.image_key in keys:
            raise ManifestError("Image annotée dupliquée")
        keys.add(row.image_key)
        if groups.setdefault(row.video_id, row.split) != row.split:
            raise ManifestError("Fuite de vidéo dans le dataset de détection")
        path = storage.path(row.image_key)
        if file_hash(path) != row.sha256:
            raise ManifestError("Image modifiée depuis la validation des boîtes")
        if hashes.setdefault(row.sha256, row.split) != row.split:
            raise ManifestError("Image identique dans plusieurs splits")
        with Image.open(path) as image:
            image.verify()
    return {
        "images": len(source.images),
        "boxes": sum(len(row.boxes) for row in source.images),
        "dataset_valid": True,
        "training_available": False,
        "reason": "Aucun adaptateur de fine-tuning validé n'est fourni pour ce modèle",
    }


def train_detector(config: DetectorTrainingConfig) -> Path:
    validate_detector_dataset(config)
    raise ModelError(
        f"Fine-tuning indisponible pour {config.model_id}/{config.backend}. "
        "Un adaptateur doit vérifier le format d'entraînement et les poids ; "
        "les checkpoints MegaDetector v5 ne sont pas des poids Ultralytics arbitraires."
    )
