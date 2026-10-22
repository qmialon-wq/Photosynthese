"""Snapshot explicite du POC : labels provisoires et priorité aux revues humaines."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..classes import load_classes
from ..commands import training_samples
from ..config import VisionSettings
from ..datasets.inventory import file_hash
from ..errors import ManifestError
from ..schemas import Box, CropRecord, CropsManifest, FrameRecord, Inventory
from ..storage import LocalStorage


def merge_reviews(
    manifest: CropsManifest, inventory: Inventory, reviews: list[dict[str, Any]]
) -> tuple[CropsManifest, dict[str, Any]]:
    if manifest.class_manifest_version != inventory.class_manifest_version:
        raise ManifestError("Manifestes de classes incompatibles")
    by_id = {video.video_id: video for video in inventory.videos}
    by_hash = {video.content_hash: video for video in inventory.videos if video.content_hash}
    groups: dict[str, set[str | None]] = defaultdict(set)
    for video in inventory.videos:
        if video.content_hash:
            groups[video.content_hash].add(video.split)
    if any(len(splits) > 1 for splits in groups.values()):
        raise ManifestError("Copies vidéo présentes dans plusieurs ensembles")
    reviewed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reviews:
        if row["video_id"] in by_hash:
            reviewed[row["video_id"]].append(row)
    crops, revisions = [], []
    for crop in manifest.crops:
        video = by_id.get(crop.frame.video_id)
        if video is None or not video.content_hash or crop.frame.split != video.split:
            raise ManifestError("Vidéo absente de l'inventaire ou séparation incompatible")
        if video.content_hash not in reviewed:
            crops.append(
                crop.model_copy(
                    update={"frame": crop.frame.model_copy(update={"group_id": video.content_hash})}
                )
            )
    # Remplacer tous les crops provisoires de la vidéo revue, sans réintroduire un rejet.
    for digest, rows in reviewed.items():
        video = by_hash[digest]
        split = "test" if any(row["test_locked"] for row in rows) else video.split
        for row in rows:
            revisions.append(
                {
                    "sample_id": row["id"],
                    "revision": row["revision"],
                    "state": row["state"],
                    "review_split": row["split"],
                    "effective_split": split,
                }
            )
            if row["state"] not in ("validated", "corrected"):
                continue
            if row["render_status"] != "ready" or not row["crop_key"]:
                raise ManifestError("Attendre le rendu des corrections humaines")
            crops.append(
                CropRecord(
                    crop_id=row["id"],
                    image_key=row["crop_key"],
                    review="accept",
                    label=row["label"],
                    detection_confidence=row["detection_score"],
                    box=Box(**row["box"]),
                    frame=FrameRecord(
                        video_id=video.video_id,
                        group_id=digest,
                        frame_index=row["frame_index"],
                        time_seconds=row["time_seconds"],
                        image_key=row["original_image_key"],
                        split=split,
                        species_candidate=video.species_candidate,
                    ),
                )
            )
    return CropsManifest(
        class_manifest_version=manifest.class_manifest_version, crops=tuple(crops)
    ), {
        "human_revisions": revisions,
        "replaced_video_hashes": sorted(reviewed),
        "ignored_review_video_hashes": sorted({r["video_id"] for r in reviews} - set(by_hash)),
    }


def prepare_snapshot(settings: VisionSettings) -> None:
    """Geler les sources et révisions courantes, ou réutiliser le snapshot d'une reprise."""
    if settings.train_manifest is None:
        raise ManifestError("Fournir la destination du manifeste dédié au POC")
    storage = LocalStorage(settings.output_root)
    target_key = settings.train_manifest.resolve().relative_to(storage.root).as_posix()
    if not settings.train_manifest.exists():
        from shared.review.database import transaction
        from shared.review.service import SAMPLE_QUERY

        source = storage.path("training.json")
        inventory = storage.path("classification/videos.json")
        with transaction() as connection:
            reviews = connection.execute(SAMPLE_QUERY + " ORDER BY s.id").fetchall()
        snapshot, audit = merge_reviews(
            CropsManifest.model_validate_json(source.read_text(encoding="utf-8")),
            Inventory.model_validate_json(inventory.read_text(encoding="utf-8")),
            reviews,
        )
        storage.write_json(target_key, snapshot.model_dump(mode="json"))
        storage.write_json(
            str(Path(target_key).with_name("provenance.json")),
            {
                **audit,
                "source_sha256": file_hash(source),
                "inventory_sha256": file_hash(inventory),
                "policy": "filename_provisional_with_human_overrides",
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--submit", action="store_true", help="Soumettre à Redis après vérification"
    )
    args = parser.parse_args()
    settings = VisionSettings.model_validate_json(args.config.read_text(encoding="utf-8"))
    classes = load_classes(settings.classes_manifest)
    prepare_snapshot(settings)
    # Un snapshot existant est réutilisé sans le remplacer, notamment pour la reprise.
    samples = training_samples(settings, classes)
    summary = {
        "run_id": settings.training.run_id,
        "manifest": str(settings.train_manifest),
        "manifest_sha256": file_hash(settings.train_manifest),
        "splits": dict(Counter(r.frame.split for r in samples)),
        "reviews": dict(Counter(r.review for r in samples)),
        "model": settings.training.model_name,
    }
    if args.submit:
        from .commands import enqueue_training

        summary["job"] = enqueue_training(settings)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
