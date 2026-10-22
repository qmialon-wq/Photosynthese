"""Préparer des recadrages avec labels provisoires, sans prétendre les valider."""

import logging
from typing import Any

from ..classes import ClassManifest
from ..config import VisionSettings
from ..detection.base import Detector
from ..detection.batch import detect_frames
from ..errors import ManifestError
from ..schemas import CropsManifest, Inventory
from ..storage import LocalStorage
from .crops import build_crops
from .frames import extract_frames


def prepare_training(
    source: Inventory,
    detector: Detector,
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
) -> dict[str, Any]:
    if source.class_manifest_version != classes.version or not source.videos:
        raise ManifestError("Inventaire vide ou incompatible")
    if any(video.split is None for video in source.videos if not video.error):
        raise ManifestError("Séparer les vidéos avant la préparation")
    reviews = {}
    review_path = storage.path("review.json")
    if review_path.is_file():
        review = CropsManifest.model_validate_json(review_path.read_text(encoding="utf-8"))
        if review.class_manifest_version != classes.version:
            raise ManifestError("Revue incompatible avec les classes")
        if len({r.crop_id for r in review.crops}) != len(review.crops):
            raise ManifestError("Identifiants de revue dupliqués")
        reviews = {r.crop_id: r for r in review.crops if r.review != "pending"}
    logger = logging.getLogger(__name__)
    logger.info("Extraction des images de %s vidéos", len(source.videos))
    frames = extract_frames(source, storage, settings.frames)
    logger.info("Détection MegaDetector sur %s images", len(frames.frames))
    detections = detect_frames(frames, detector, storage)
    logger.info("Recadrage des animaux détectés")
    crops = build_crops(detections, storage, settings.crops)
    records = []
    for crop in crops:
        reviewed = reviews.get(crop.crop_id)
        if reviewed is not None:
            if (
                reviewed.frame.video_id != crop.frame.video_id
                or reviewed.frame.image_key != crop.frame.image_key
            ):
                raise ManifestError("Identité de recadrage incohérente avec la revue")
            # Garder le label, le refus et le recadrage corrigé ; actualiser le split source.
            crop = reviewed.model_copy(update={"frame": crop.frame})
        elif crop.frame.species_candidate in classes.names:
            crop = crop.model_copy(update={"label": crop.frame.species_candidate})
        records.append(crop)
    storage.write_json(
        "training.json",
        CropsManifest(class_manifest_version=classes.version, crops=tuple(records)).model_dump(
            mode="json"
        ),
    )
    summary = {
        "videos": len(source.videos),
        "frames": len(frames.frames),
        "crops": len(records),
        "errors": len(frames.issues) + sum(r.error is not None for r in detections.frames),
        "filename_labeled_crops": sum(
            r.review == "pending" and r.label is not None for r in records
        ),
        "human_reviewed_crops": sum(r.review != "pending" for r in records),
        "label_source": "filename_provisional_unless_human_reviewed",
        "manifest": str(storage.path("training.json")),
    }
    storage.write_json("preparation.json", summary)
    return summary
