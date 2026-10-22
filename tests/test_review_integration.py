"""Base isolée par schéma ; détecteur synthétique réservé aux tests, aucun GPU."""

import importlib.util
import json
import os
import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import cv2
import numpy as np
import psycopg
import pytest
from app.main import app
from biosentinelle_vision.classes import load_classes
from biosentinelle_vision.config import FramesConfig, VisionSettings
from biosentinelle_vision.review import operations
from biosentinelle_vision.review.exporting import archive, snapshot
from biosentinelle_vision.review.importing import prepare_import
from biosentinelle_vision.review.operations import execute_operation, render_revision
from biosentinelle_vision.schemas import Box, CropsManifest, Detection
from biosentinelle_vision.storage import LocalStorage
from fastapi.testclient import TestClient
from psycopg import sql

from shared.review import database, service
from shared.review.database import ReviewError, transaction
from shared.review.outbox import publish_pending
from shared.review.schemas import BatchDecision, DatasetRequest, Decision, ImportVideo

pytestmark = pytest.mark.integration


@pytest.fixture
def review_db(monkeypatch, tmp_path):
    schema = "test_review_" + uuid4().hex
    kwargs = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "dbname": os.getenv("POSTGRES_DB", "biosentinelle"),
        "user": os.getenv("POSTGRES_USER", "biosentinelle"),
        "password": os.getenv("POSTGRES_PASSWORD", "biosentinelle_local"),
    }
    admin = psycopg.connect(**kwargs, autocommit=True)
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def connect():
        return psycopg.connect(
            **kwargs, options=f"-c search_path={schema},public -c statement_timeout=3000"
        )

    monkeypatch.setattr(database, "connect", connect)
    migration_path = Path("backend/migrations/versions/0003_human_review.py")
    spec = importlib.util.spec_from_file_location("review_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with connect() as connection:
            monkeypatch.setattr(migration.op, "execute", connection.execute)
            migration.upgrade()
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
        yield VisionSettings(
            dataset_root=tmp_path / "datasets",
            inbox_root=tmp_path / "datasets/inbox",
            output_root=tmp_path / "results/vision",
            frames=FramesConfig(max_per_video=3, min_seconds_between=0.1),
        )
    finally:
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


class TestDetector:
    __test__ = False
    identity = "synthetic-test-detector-v1"

    def __init__(self, empty=False):
        self.empty = empty

    def detect(self, image):
        return (
            () if self.empty else (Detection(box=Box(x=0.1, y=0.1, w=0.5, h=0.5), confidence=0.9),)
        )


def import_fixture(settings, *, split="train", name="chevreuil.mp4", seed=1, empty=False):
    settings.inbox_root.mkdir(parents=True, exist_ok=True)
    source = settings.inbox_root / name
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5, (96, 96))
    assert writer.isOpened()
    random = np.random.default_rng(seed)
    for _ in range(4):
        writer.write(random.integers(0, 256, (96, 96, 3), dtype=np.uint8))
    writer.release()
    request = ImportVideo(video=name, split=split)
    job = service.submit("import_video", request.model_dump(), "alice")
    result = prepare_import(
        request, service.get_operation(job["id"]), settings, load_classes(), TestDetector(empty)
    )
    return result


def validate(sample, label="chevreuil", **kwargs):
    return service.decide(
        sample["id"],
        Decision(
            expected_revision=sample["revision"],
            decision="validate",
            label=label,
            reason="Vérification humaine",
            **kwargs,
        ),
        "alice",
    )


def test_batch_without_comment_or_reviewer_keeps_audit_and_boxes(review_db):
    import_fixture(review_db)
    samples = service.list_samples(None, None, None, 50, 0)
    with TestClient(app) as client:
        response = client.post(
            "/review/samples/batch-decisions",
            json={
                "items": [
                    {"sample_id": sample["id"], "expected_revision": 0} for sample in samples
                ],
                "decision": "validate",
                "label": "renards",
            },
        )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 3
    for original, updated in zip(samples, response.json(), strict=True):
        assert updated["label"] == "renards" and updated["revision"] == 1
        assert updated["box"] == original["box"]
        assert updated["actor"] == "local"
        assert updated["provenance"]["reason_source"] == "automatic"
        assert updated["provenance"]["reason"]
        assert updated["provenance"]["supplied"]["action"] == "batch"
        assert len(service.history(updated["id"])) == 2


def test_batch_stale_revision_rolls_back_all_decisions_and_outbox(review_db):
    import_fixture(review_db)
    samples = service.list_samples(None, None, None, 50, 0)
    validate(samples[1])
    with transaction() as connection:
        before = connection.execute("SELECT count(*) AS n FROM review_operations").fetchone()["n"]
    batch = BatchDecision(
        items=[{"sample_id": sample["id"], "expected_revision": 0} for sample in samples],
        decision="reject",
    )
    with pytest.raises(ReviewError, match="obsolète"):
        service.decide_batch(batch, "alice")
    assert service.get_sample(samples[0]["id"])["revision"] == 0
    assert service.get_sample(samples[2]["id"])["revision"] == 0
    with transaction() as connection:
        after = connection.execute("SELECT count(*) AS n FROM review_operations").fetchone()["n"]
    assert after == before


def test_batch_test_lock_rolls_back_other_samples(review_db):
    import_fixture(review_db)
    samples = service.list_samples(None, None, None, 50, 0)
    test_video = import_fixture(review_db, split="test", name="test.mp4", seed=42)
    locked = service.list_samples(None, None, None, 50, 0, test_video["video_id"])[0]
    with transaction(write=True) as connection:
        connection.execute(
            "UPDATE review_groups SET test_locked=true WHERE id=%s", (locked["group_id"],)
        )
    with TestClient(app) as client:
        response = client.post(
            "/review/samples/batch-decisions",
            json={
                "items": [
                    {"sample_id": item["id"], "expected_revision": 0}
                    for item in [samples[0], locked]
                ],
                "decision": "reject",
            },
        )
    assert response.status_code == 409, response.text
    assert service.get_sample(samples[0]["id"])["revision"] == 0


def test_single_reject_without_comment_is_audited(review_db):
    import_fixture(review_db)
    sample = service.list_samples(None, None, None, 1, 0)[0]
    with TestClient(app) as client:
        response = client.post(
            f"/review/samples/{sample['id']}/decisions",
            json={
                "expected_revision": 0,
                "decision": "reject",
            },
        )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "rejected"
    assert response.json()["provenance"]["reason"] == "Rejet manuel"


def test_api_correction_history_and_reproducible_export(review_db):
    result = import_fixture(review_db)
    samples = service.list_samples(None, None, None, 50, 0)
    assert len(samples) == 3
    assert all(row["state"] == "pending" and row["label"] is None for row in samples)
    item = samples[0]
    with TestClient(app) as client:
        assert (
            client.post(
                f"/review/samples/{item['id']}/decisions",
                json={
                    "expected_revision": 0,
                    "decision": "validate",
                    "label": "espece_inconnue",
                    "reason": "Correction",
                },
            ).status_code
            == 422
        )
        response = client.post(
            f"/review/samples/{item['id']}/decisions",
            headers={"X-Reviewer": "bob"},
            json={
                "expected_revision": 0,
                "decision": "validate",
                "label": "renards",
                "reason": "Correction espèce et boîte",
                "box": {"x": 0.3, "y": 0.2, "w": 0.4, "h": 0.5},
            },
        )
        assert response.status_code == 200, response.text
        row = response.json()
        assert row["state"] == "corrected" and row["render_status"] == "pending"
        assert client.get(f"/review/samples/{item['id']}/images/crop").status_code == 409
        assert client.get(f"/review/samples/{item['id']}/images/original").status_code == 200
        assert (
            client.post(
                f"/review/samples/{item['id']}/decisions",
                headers={"X-Reviewer": "bob"},
                json={"expected_revision": 0, "decision": "reject", "reason": "stale"},
            ).status_code
            == 409
        )
        op = service.get_operation(row["render_operation_id"])
        render_revision(op["payload"], LocalStorage(review_db.output_root))
        history = client.get(f"/review/samples/{item['id']}/history").json()
        assert (
            history[1]["actor"] == "bob"
            and history[1]["provenance"]["reason"] == "Correction espèce et boîte"
        )
        assert history[0]["crop_key"] != history[1]["crop_key"]
        rejected = service.decide(
            samples[1]["id"],
            Decision(expected_revision=0, decision="reject", reason="Animal inexploitable"),
            "bob",
        )
        assert rejected["state"] == "rejected"
        request = DatasetRequest(name="review-test")
        version = snapshot(request, "bob", load_classes())
        first = archive(version, LocalStorage(review_db.output_root))
        assert snapshot(request, "bob", load_classes()) == version
        content = client.get(first["download_url"]).content
        validate(service.get_sample(item["id"]), "sanglier")
        rebuilt = archive(version, LocalStorage(review_db.output_root))
        assert rebuilt["archive_sha256"] == first["archive_sha256"]
        assert client.get(first["download_url"]).content == content
        path = review_db.output_root / f"review/exports/{version}/dataset.zip"
        with zipfile.ZipFile(path) as archive_file:
            training = CropsManifest.model_validate_json(archive_file.read("training.json"))
            assert len(training.crops) == 1 and training.crops[0].label == "renards"
            assert all(crop.review == "accept" for crop in training.crops)
            assert json.loads(archive_file.read("manifest.json"))["samples"][0]["revision"] == 1
        assert client.get("/review/videos").json()[0]["id"] == result["video_id"]


def test_test_freeze_and_database_guards(review_db):
    import_fixture(review_db, split="test")
    item = validate(service.list_samples(None, None, None, 50, 0)[0])
    request = DatasetRequest(name="test-protected")
    version = snapshot(request, "alice", load_classes())
    assert snapshot(request, "alice", load_classes()) == version
    with pytest.raises(ReviewError, match="gelé"):
        validate(item, "renards")
    with pytest.raises(psycopg.errors.CheckViolation):
        with transaction(write=True) as connection:
            connection.execute("UPDATE review_groups SET split='train'")
    with pytest.raises(psycopg.errors.CheckViolation):
        with transaction(write=True) as connection:
            connection.execute(
                "UPDATE review_revisions SET label='sanglier' WHERE sample_id=%s", (item["id"],)
            )
    with pytest.raises(psycopg.errors.CheckViolation):
        with transaction(write=True) as connection:
            connection.execute("DELETE FROM review_dataset_items")


def test_no_detection_and_duplicate_import(review_db):
    first = import_fixture(review_db, empty=True)
    assert first["detections"] == 0
    assert (
        service.list_videos("no_detections", 50, 0)[0]["diagnostics"]["scope"]
        == "sampled_frames_only"
    )
    assert not service.list_samples(None, None, None, 50, 0)
    request = ImportVideo(video="chevreuil.mp4", split="test")
    op = service.submit("import_video", request.model_dump(), "bob")
    with pytest.raises(ReviewError, match="Split"):
        prepare_import(
            request, service.get_operation(op["id"]), review_db, load_classes(), TestDetector()
        )


def test_cross_split_duplicates_block_snapshot(review_db):
    import_fixture(review_db, split="train")
    original = review_db.inbox_root / "chevreuil.mp4"
    duplicate = review_db.inbox_root / "autre.mp4"
    shutil.copyfile(original, duplicate)
    with duplicate.open("ab") as stream:
        stream.write(b"different-video-container")
    request = ImportVideo(video="autre.mp4", split="test")
    op = service.submit("import_video", request.model_dump(), "bob")
    prepare_import(
        request, service.get_operation(op["id"]), review_db, load_classes(), TestDetector()
    )
    for item in service.list_samples(None, None, None, 50, 0):
        validate(item)
    with pytest.raises(ReviewError, match="Fuite"):
        snapshot(DatasetRequest(name="leaking"), "alice", load_classes())


def test_outbox_and_idempotent_recovery(review_db, monkeypatch):
    operation = service.submit("rebuild_export", {"dataset_id": "test"}, "alice")
    redis = MagicMock()
    assert publish_pending(redis) == 1
    assert publish_pending(redis) == 0
    calls = []

    def perform(row, settings, classes):
        calls.append(row["id"])
        return {"dataset_id": "test"}

    monkeypatch.setattr(operations, "perform", perform)
    first = execute_operation(operation["id"], review_db, load_classes())
    assert execute_operation(operation["id"], review_db, load_classes()) == first
    assert len(calls) == 1 and service.get_operation(operation["id"])["status"] == "completed"


def test_unreadable_video_reports_operation_error(review_db, monkeypatch):
    review_db.inbox_root.mkdir(parents=True)
    (review_db.inbox_root / "broken.mp4").write_bytes(b"not a video")
    request = ImportVideo(video="broken.mp4", split="train")
    operation = service.submit("import_video", request.model_dump(), "alice")

    def perform(row, settings, classes):
        return prepare_import(request, row, settings, classes, TestDetector())

    monkeypatch.setattr(operations, "perform", perform)
    with pytest.raises(ReviewError, match="illisible"):
        execute_operation(operation["id"], review_db, load_classes())
    assert service.get_operation(operation["id"])["status"] == "error"
    assert not service.list_videos("no_detections", 50, 0)


def test_priority_and_outbox_survive_redis_failure(review_db):
    import_fixture(review_db)
    first, second, _ = service.list_samples(None, None, None, 50, 0)
    validate(first, "chevreuil")
    rows = service.list_samples("pending", None, None, 50, 0)
    before = rows[0]["priority"]
    validate(second, "renards")
    assert service.list_samples("pending", None, None, 50, 0)[0]["priority"] == before
    # Nouvelle boîte : révision + rendu dans une même transaction PostgreSQL.
    updated = validate(
        service.get_sample(first["id"]), box=Box(x=0.2, y=0.2, w=0.6, h=0.6).model_dump()
    )
    redis = MagicMock()
    redis.pipeline.side_effect = ConnectionError("Redis hors ligne")
    with pytest.raises(ConnectionError):
        publish_pending(redis)
    assert service.get_sample(first["id"])["revision"] == updated["revision"]
    assert service.get_operation(updated["render_operation_id"])["published_at"] is None
    assert publish_pending(MagicMock()) > 0


def test_pending_render_blocks_snapshot_and_blob_corruption_blocks_rebuild(review_db):
    import_fixture(review_db)
    item = service.list_samples(None, None, None, 50, 0)[0]
    updated = validate(item, box=Box(x=0.2, y=0.2, w=0.6, h=0.6).model_dump())
    with pytest.raises(ReviewError, match="recadrages corrigés"):
        snapshot(DatasetRequest(name="not-ready"), "alice", load_classes())
    storage = LocalStorage(review_db.output_root)
    render_revision({"sample_id": item["id"], "revision": updated["revision"]}, storage)
    version = snapshot(DatasetRequest(name="integrity"), "alice", load_classes())
    archive(version, storage)
    storage.write_bytes(service.get_sample(item["id"])["crop_key"], b"broken")
    with pytest.raises(ReviewError, match="corrompu"):
        archive(version, storage)


def test_migration_downgrade_upgrade(review_db, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "round_trip", Path("backend/migrations/versions/0003_human_review.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with transaction() as connection:
        monkeypatch.setattr(migration.op, "execute", connection.execute)
        migration.downgrade()
        migration.upgrade()
        assert connection.execute("SELECT count(*) AS n FROM review_species").fetchone()["n"] == 10
