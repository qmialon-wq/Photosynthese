"""Enrichissement des manifestes existants ; images et splits ne sont jamais réécrits."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

from ..classes import ClassManifest, load_classes
from ..errors import ManifestError
from ..review.images import quality, similar
from ..schemas import CropsManifest, Inventory
from ..storage import LocalStorage
from ..training.dataset import select_samples


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def prepare_dataset(
    manifest: CropsManifest,
    inventory: Inventory,
    storage: LocalStorage,
    destination: LocalStorage,
    classes: ClassManifest,
    *,
    allow_weak_labels: bool = False,
    exclude_blurry: bool = True,
    min_side: int = 28,
    max_per_video: int = 18,
    margin: float = 0.12,
) -> dict[str, Any]:
    if (
        manifest.class_manifest_version != classes.version
        or inventory.class_manifest_version != classes.version
    ):
        raise ManifestError("Référentiel incompatible")
    if min_side < 1 or not 0 <= margin <= 1:
        raise ManifestError("Paramètres de qualité invalides")
    by_id = {v.video_id: v for v in inventory.videos}
    group_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    for video in inventory.videos:
        if video.split is not None:
            for kind, key in (("sequence", video.group_id), ("content", video.content_hash)):
                if key:
                    group_splits[kind, key].add(video.split)
    if any(len(splits) > 1 for splits in group_splits.values()):
        raise ManifestError("Groupe de séquences ou contenu identique entre splits")
    rejected, accepted, details = [], [], []
    for record in manifest.crops:
        video = by_id.get(record.frame.video_id)
        if video is None or not video.content_hash or video.split != record.frame.split:
            raise ManifestError("Inventaire source ou split incompatible")
        if record.review == "reject":
            rejected.append({"crop_id": record.crop_id, "reason": "human_rejected"})
            continue
        human = record.review == "accept"
        if not human and (
            not allow_weak_labels
            or video.multispecies is True
            or len(video.candidates) != 1
            or not video.species_candidate
        ):
            rejected.append({"crop_id": record.crop_id, "reason": "human_validation_required"})
            continue
        if not human:
            record = record.model_copy(update={"label": video.species_candidate})
        if record.label not in classes.names:
            raise ManifestError("Espèce absente du référentiel actif")
        try:
            image_bytes = storage.read_bytes(record.image_key)
            with Image.open(storage.path(record.image_key)) as image:
                descriptor = quality(image.convert("RGB"))
        except (OSError, ValueError) as exc:
            rejected.append({"crop_id": record.crop_id, "reason": "unreadable", "error": str(exc)})
            continue
        if (
            descriptor["blurry"]
            and exclude_blurry
            or min(descriptor["width"], descriptor["height"]) < min_side
        ):
            rejected.append({"crop_id": record.crop_id, "reason": "blurry_or_too_small"})
            continue
        frame = record.frame.model_copy(
            update={
                "group_id": video.group_id or video.content_hash,
                "species_candidate": video.species_candidate,
            }
        )
        record = record.model_copy(update={"frame": frame})
        accepted.append(record)
        details.append(
            {
                "crop_id": record.crop_id,
                "image_key": record.image_key,
                "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
                "source_video": video.relative_path,
                "source_video_sha256": video.content_hash,
                "group_id": frame.group_id,
                "frame_index": frame.frame_index,
                "time_seconds": frame.time_seconds,
                "box": record.box.model_dump(),
                "label": record.label,
                "label_source": "human" if human else "filename_weak",
                "split": frame.split,
                "quality": descriptor,
                "margin_assumption": margin,
                "foreground_fraction_method": "geometric_prior_not_measured",
                "foreground_fraction_estimate": 1 / (1 + 2 * margin) ** 2,
            }
        )
    # Identiques et quasi-identiques : index LSH, puis vérification dHash + pixel MAD.
    # Cinq bandes suffisent à conserver tous les candidats à distance de Hamming <=4.
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    duplicate_pairs = []
    for index, row in enumerate(details):
        digest = int(row["quality"]["dhash"], 16)
        keys = [(band, digest >> (band * 13) & 8191) for band in range(5)]
        candidates = set(i for key in keys for i in buckets[key])
        for previous in sorted(candidates):
            other = details[previous]
            if row["image_sha256"] == other["image_sha256"] or similar(
                row["quality"], other["quality"]
            ):
                if row["split"] != other["split"]:
                    raise ManifestError(
                        f"Quasi-doublons entre splits : {other['crop_id']}/{row['crop_id']}. "
                        "Regrouper les séquences avant de figer le test."
                    )
                duplicate_pairs.append([other["crop_id"], row["crop_id"]])
        for key in keys:
            buckets[key].append(index)
    selected = select_samples(
        accepted, classes, max_per_video, allow_filename_labels=allow_weak_labels
    )
    selected_ids = {r.crop_id for r in selected}
    details = [row for row in details if row["crop_id"] in selected_ids]
    counts: dict[str, dict[str, int]] = {}
    warnings = [
        "L'indépendance des prises reste limitée en l'absence de groupes de séquences fiables."
    ]
    for split in ("train", "val", "test"):
        counts[split] = dict(Counter(r.label for r in selected if r.frame.split == split))
        for name in classes.names:
            videos = {
                r.frame.video_id for r in selected if r.frame.split == split and r.label == name
            }
            if len(videos) < 3:
                warnings.append(
                    f"{split}/{name} : {len(videos)} vidéos, représentation insuffisante"
                )
    snapshot = {
        "schema_version": "classification-dataset-1",
        "classes": classes.model_dump(mode="json"),
        "samples": details,
        "counts": counts,
        "excluded": rejected,
        "duplicate_pairs": duplicate_pairs,
        "policy": {
            "allow_weak_labels": allow_weak_labels,
            "exclude_blurry": exclude_blurry,
            "min_side": min_side,
            "max_per_video": max_per_video,
            "margin": margin,
        },
        "warnings": warnings,
    }
    version = hashlib.sha256(canonical(snapshot)).hexdigest()
    target = destination.path(f"{version}/manifest.json")
    if target.exists() and target.read_bytes() != canonical(snapshot):
        raise ManifestError("Version de dataset incohérente")
    destination.write_bytes(f"{version}/manifest.json", canonical(snapshot))
    destination.write_json(
        f"{version}/training.json",
        CropsManifest(class_manifest_version=classes.version, crops=selected).model_dump(
            mode="json"
        ),
    )
    return {
        "dataset_version": version,
        "samples": len(selected),
        "counts": counts,
        "manifest": str(target),
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "inventory", "storage-root", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--allow-weak-labels", action="store_true")
    parser.add_argument("--keep-blurry", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_dataset(
                CropsManifest.model_validate_json(args.manifest.read_text(encoding="utf-8")),
                Inventory.model_validate_json(args.inventory.read_text(encoding="utf-8")),
                LocalStorage(args.storage_root),
                LocalStorage(args.output),
                load_classes(),
                allow_weak_labels=args.allow_weak_labels,
                exclude_blurry=not args.keep_blurry,
            )
        )
    )


if __name__ == "__main__":
    main()
