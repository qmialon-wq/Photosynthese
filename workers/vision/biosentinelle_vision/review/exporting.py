import hashlib
import json
import os
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from shared.review.database import ReviewError, jsonb, transaction
from shared.review.schemas import DatasetRequest
from shared.review.service import SAMPLE_QUERY

from ..classes import ClassManifest
from ..datasets.inventory import file_hash
from ..schemas import Box, CropRecord, CropsManifest, FrameRecord
from ..storage import LocalStorage
from .images import similar


def canonical(value: Any) -> bytes:
    def encode(item: Any) -> str:
        if isinstance(item, date | datetime):
            return item.isoformat()
        raise TypeError(type(item).__name__)

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=encode,
    ).encode("utf-8")


def guard_leakage(connection: Any, selected: list[dict[str, Any]]) -> None:
    selected_frames = {row["frame_id"]: row["split"] for row in selected}
    # Même un test non encore validé ne doit pas réapparaître dans le train.
    test_frames = {
        row["id"]
        for row in connection.execute("""SELECT f.id FROM review_frames f
       JOIN review_videos v ON v.id=f.video_id JOIN review_groups g ON g.id=v.group_id
       WHERE g.split='test'""").fetchall()
    }
    for pair in connection.execute("SELECT * FROM review_similarities").fetchall():
        a, b = pair["first_id"], pair["second_id"]
        sa, sb = selected_frames.get(a), selected_frames.get(b)
        if (
            (sa and sb and sa != sb)
            or (sa and sa != "test" and b in test_frames)
            or (sb and sb != "test" and a in test_frames)
        ):
            raise ReviewError(
                f"Fuite inter-splits : images {a}/{b} ({pair['reason']}). "
                "Exclure le groupe non-test."
            )
    for index, first in enumerate(selected):
        for second in selected[index + 1 :]:
            if first["split"] != second["split"] and (
                first["crop_sha256"] == second["crop_sha256"]
                or similar(first["quality"], second["quality"])
            ):
                raise ReviewError(
                    f"Recadrages identiques ou proches entre splits : {first['id']}/{second['id']}"
                )
    tests = connection.execute(
        SAMPLE_QUERY + " WHERE g.split='test' AND r.render_status='ready'"
    ).fetchall()
    for first in selected:
        if first["split"] == "test":
            continue
        for second in tests:
            if first["crop_sha256"] == second["crop_sha256"] or similar(
                first["quality"], second["quality"]
            ):
                raise ReviewError(
                    f"Fuite vers un recadrage test, même non validé : {first['id']}/{second['id']}"
                )


def snapshot(request: DatasetRequest, actor: str, classes: ClassManifest) -> str:
    with transaction(write=True) as connection:
        rows = connection.execute(
            SAMPLE_QUERY
            + " WHERE r.state IN ('validated','corrected') AND v.status='ready' ORDER BY s.id"
        ).fetchall()
        rows = [
            row
            for row in rows
            if row["group_id"] not in request.exclude_groups
            and not any(
                (row["quality"] or {}).get(flag) or row["frame_quality"].get(flag)
                for flag in request.exclude_quality
            )
        ]
        if not rows:
            raise ReviewError("Aucun recadrage validé pour cette sélection", 422)
        if any(row["render_status"] != "ready" or not row["crop_sha256"] for row in rows):
            raise ReviewError("Attendre la fin des recadrages corrigés avant de versionner")
        guard_leakage(connection, rows)
        for row in rows:
            row.pop("test_locked")
            row["history"] = connection.execute(
                "SELECT * FROM review_revisions WHERE sample_id=%s AND revision<=%s "
                "ORDER BY revision",
                (row["id"], row["revision"]),
            ).fetchall()
        # Aucun état courant n'est relu lors de la reconstruction.
        manifest = json.loads(
            canonical(
                {
                    "schema_version": "review-dataset-1",
                    "name": request.name,
                    "classes": classes.model_dump(mode="json"),
                    "selection": request.model_dump(),
                    "samples": rows,
                }
            )
        )
        identifier = hashlib.sha256(canonical(manifest)).hexdigest()
        connection.execute(
            (
                "INSERT INTO review_datasets(id,name,manifest,actor) VALUES(%s,%s,%s,%s) ON "
                "CONFLICT DO NOTHING"
            ),
            (identifier, request.name, jsonb(manifest), actor),
        )
        for row in rows:
            connection.execute(
                "INSERT INTO review_dataset_items VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (identifier, row["id"], row["revision"], row["split"]),
            )
            if row["split"] == "test":
                connection.execute(
                    (
                        "UPDATE review_groups SET test_locked=true,"
                        "locked_at=coalesce(locked_at,now()) "
                        "WHERE id=%s"
                    ),
                    (row["group_id"],),
                )
        return identifier


def archive(identifier: str, storage: LocalStorage) -> dict[str, str]:
    with transaction() as connection:
        dataset = connection.execute(
            "SELECT * FROM review_datasets WHERE id=%s", (identifier,)
        ).fetchone()
    if dataset is None:
        raise ReviewError("Dataset inconnu", 404)
    manifest = dataset["manifest"]
    crops, files = [], {}
    for row in manifest["samples"]:
        image_key = f"images/{row['crop_sha256']}.jpg"
        original = f"originals/{row['original_sha256']}.jpg"
        files[image_key] = (row["crop_key"], row["crop_sha256"])
        files[original] = (row["original_image_key"], row["original_sha256"])
        crops.append(
            CropRecord(
                crop_id=row["id"],
                image_key=image_key,
                review="accept",
                label=row["label"],
                detection_confidence=row["detection_score"],
                box=Box(**row["box"]),
                frame=FrameRecord(
                    video_id=row["video_id"],
                    group_id=row["group_id"],
                    frame_index=row["frame_index"],
                    time_seconds=row["time_seconds"],
                    image_key=original,
                    split=row["split"],
                    species_candidate=row["species_candidate"],
                ),
            )
        )
    training = CropsManifest(
        class_manifest_version=manifest["classes"]["version"], crops=tuple(crops)
    )
    texts = {
        "manifest.json": canonical(manifest),
        "classes.json": canonical(manifest["classes"]),
        "training.json": canonical(training.model_dump(mode="json")),
    }
    key = f"review/exports/{identifier}/dataset.zip"
    target = storage.path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as output:
            for name in sorted(set(files) | set(texts)):
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system, entry.external_attr = 3, 0o100644 << 16
                if name in texts:
                    data = texts[name]
                else:
                    source, expected = files[name]
                    data = storage.read_bytes(source)
                    if hashlib.sha256(data).hexdigest() != expected:
                        raise ReviewError(f"Blob absent ou corrompu : {source}")
                output.writestr(entry, data)
        digest = file_hash(Path(temporary))
        if dataset["archive_sha256"] and dataset["archive_sha256"] != digest:
            raise ReviewError("Reconstruction différente de l'archive publiée")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    with transaction(write=True) as connection:
        connection.execute(
            "UPDATE review_datasets SET archive_key=%s,archive_sha256=%s WHERE id=%s",
            (key, digest, identifier),
        )
    return {
        "dataset_id": identifier,
        "archive_sha256": digest,
        "download_url": f"/review/datasets/{identifier}/archive",
    }
