import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from shared.review.database import ReviewError, jsonb, transaction
from shared.review.schemas import ImportVideo

from ..classes import ClassManifest
from ..config import VisionSettings
from ..datasets.frames import extract_frames
from ..datasets.inventory import VIDEO_EXTENSIONS, file_hash, species_candidates
from ..schemas import Inventory, VideoRecord
from ..storage import LocalStorage
from .images import blob, quality, render, similar


def copy_video(source: Path, target: Path, digest: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if file_hash(target) != digest:
            raise ReviewError("Source archivée corrompue")
        return
    descriptor, temporary = tempfile.mkstemp(dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as stream:
            shutil.copyfileobj(stream, output)
            output.flush()
            os.fsync(output.fileno())
        if file_hash(Path(temporary)) != digest:
            raise ReviewError("Vidéo modifiée pendant son import")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare_import(
    request: ImportVideo,
    operation: dict[str, Any],
    settings: VisionSettings,
    classes: ClassManifest,
    detector: Any,
    classifier: Any = None,
) -> dict[str, Any]:
    root = settings.inbox_root.resolve()
    source = (root / request.video).resolve()
    if (
        not source.is_relative_to(root)
        or not source.is_file()
        or source.suffix.lower() not in VIDEO_EXTENSIONS
    ):
        raise ReviewError("Vidéo absente ou hors inbox", 422)
    identifier = file_hash(source)
    group = request.group_id or identifier
    bucket = int(hashlib.sha256(f"{settings.seed}:{group}".encode()).hexdigest()[:8], 16) / 2**32
    split = request.split or (
        "test"
        if bucket < settings.split.test_fraction
        else "val"
        if bucket < settings.split.test_fraction + settings.split.validation_fraction
        else "train"
    )
    key = f"imported/{identifier}/original{source.suffix.lower()}"
    datasets = LocalStorage(settings.dataset_root)
    copy_video(source, datasets.path(key), identifier)
    candidates = species_candidates(source, classes)
    with transaction(write=True) as connection:
        species = connection.execute(
            "SELECT name FROM review_species ORDER BY class_index"
        ).fetchall()
        if tuple(row["name"] for row in species) != classes.names:
            raise ReviewError("Manifeste de classes incompatible avec la base")
        previous = connection.execute(
            "SELECT * FROM review_videos WHERE id=%s", (identifier,)
        ).fetchone()
        if previous:
            if request.group_id and previous["group_id"] != group:
                raise ReviewError("Vidéo déjà affectée à un autre groupe")
            group = previous["group_id"]
        connection.execute(
            "INSERT INTO review_groups(id,split) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (group, split),
        )
        assignment = connection.execute(
            "SELECT * FROM review_groups WHERE id=%s", (group,)
        ).fetchone()
        if request.split and assignment["split"] != request.split:
            raise ReviewError("Split du groupe immuable")
        split = assignment["split"]
        if not previous:
            if assignment["test_locked"]:
                raise ReviewError("Groupe test gelé")
            connection.execute(
                """INSERT INTO review_videos(id,group_id,source_key,original_name,
                species_candidate,candidates)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (
                    identifier,
                    group,
                    key,
                    source.name,
                    candidates[0] if len(candidates) == 1 else None,
                    jsonb(candidates),
                ),
            )
        connection.execute(
            """INSERT INTO review_imports(id,video_id,original_name,actor,provenance)
          VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (
                operation["id"],
                identifier,
                source.name,
                operation["actor"],
                jsonb({"inbox": request.video, "label_source": "filename_provisional"}),
            ),
        )
        if previous and previous["status"] in ("ready", "no_detections"):
            return {"video_id": identifier, "reused": True}
        connection.execute(
            "UPDATE review_videos SET status='processing' WHERE id=%s", (identifier,)
        )
    storage = LocalStorage(settings.output_root)
    inventory = Inventory(
        class_manifest_version=classes.version,
        dataset_root=str(datasets.root),
        videos=(
            VideoRecord(
                video_id=identifier,
                relative_path=key,
                content_hash=identifier,
                group_id=group,
                split=split,
            ),
        ),
    )
    frames = extract_frames(
        inventory, storage, settings.frames, manifest_key=f"review/imports/{identifier}/frames.json"
    )
    if frames.issues or not frames.frames:
        raise ReviewError(f"Extraction incomplète ou vidéo illisible : {frames.issues}", 422)
    sample_count = 0
    recipe = {"version": "crop-v1", "margin": settings.crops.margin, "jpeg_quality": 93}
    for frame in frames.frames:
        original_key, original_sha = blob(storage, storage.read_bytes(frame.image_key))
        frame_id = hashlib.sha256(f"{identifier}:{frame.frame_index}".encode()).hexdigest()
        with Image.open(storage.path(original_key)) as image:
            descriptor = quality(image)
            detections = detector.detect(image)
        with transaction(write=True) as connection:
            others = connection.execute(
                "SELECT id,sha256,quality FROM review_frames WHERE id<>%s", (frame_id,)
            ).fetchall()
            pairs = [
                (row["id"], "exact" if row["sha256"] == original_sha else "near")
                for row in others
                if row["sha256"] == original_sha or similar(descriptor, row["quality"])
            ]
            descriptor["near_duplicate"] = bool(pairs)
            connection.execute(
                """INSERT INTO
        review_frames(id,video_id,frame_index,time_seconds,image_key,sha256,width,height,quality)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (
                    frame_id,
                    identifier,
                    frame.frame_index,
                    frame.time_seconds,
                    original_key,
                    original_sha,
                    descriptor["width"],
                    descriptor["height"],
                    jsonb(descriptor),
                ),
            )
            for other, reason in pairs:
                first, second = sorted((frame_id, other))
                connection.execute(
                    "INSERT INTO review_similarities VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                    (first, second, reason),
                )
        for detection in detections:
            box = detection.box.model_dump()
            sample_id = hashlib.sha256(
                (frame_id + detector.identity + json.dumps(box, sort_keys=True)).encode()
            ).hexdigest()
            rendered = render(storage, original_key, box, recipe)
            rendered["quality"]["near_duplicate"] = descriptor["near_duplicate"]
            prediction = None
            if classifier:
                with Image.open(storage.path(rendered["crop_key"])) as crop:
                    prediction = classifier.predict([crop])[0]
            with transaction(write=True) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM review_samples WHERE id=%s", (sample_id,)
                ).fetchone()
                if not exists:
                    connection.execute(
                        """INSERT INTO review_samples(id,frame_id,original_box,
                        original_crop_key,detector_identity,
                      detection_score,predicted_label,classification_score,probabilities)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            sample_id,
                            frame_id,
                            jsonb(box),
                            rendered["crop_key"],
                            detector.identity,
                            detection.confidence,
                            prediction.label if prediction else None,
                            max(prediction.probabilities) if prediction else None,
                            jsonb(prediction.probabilities) if prediction else None,
                        ),
                    )
                    connection.execute(
                        """INSERT INTO review_revisions(sample_id,revision,state,label,
                        box,recipe,crop_key,
                      crop_sha256,quality,render_status,actor,provenance)
        VALUES(%s,0,'pending',NULL,%s,%s,%s,%s,%s,'ready',%s,%s)""",
                        (
                            sample_id,
                            jsonb(box),
                            jsonb(recipe),
                            rendered["crop_key"],
                            rendered["crop_sha256"],
                            jsonb(rendered["quality"]),
                            operation["actor"],
                            jsonb(
                                {
                                    "operation_id": str(operation["id"]),
                                    "label_source": "unvalidated",
                                    "detector": detector.identity,
                                    "classifier": classifier.metadata if classifier else None,
                                }
                            ),
                        ),
                    )
            sample_count += 1
    diagnostics = {
        "sampled_frames": len(frames.frames),
        "detections": sample_count,
        "scope": "sampled_frames_only",
        "frames_configuration": settings.frames.model_dump(),
        "detector": detector.identity,
    }
    with transaction(write=True) as connection:
        connection.execute(
            "UPDATE review_videos SET status=%s,diagnostics=%s WHERE id=%s",
            ("ready" if sample_count else "no_detections", jsonb(diagnostics), identifier),
        )
    return {"video_id": identifier, **diagnostics}
