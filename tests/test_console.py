import importlib.util
import json
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock

import pytest
from app.main import app
from biosentinelle_vision.classes import load_classes
from biosentinelle_vision.console_tasks import execute
from fastapi.testclient import TestClient

from shared import console
from shared.review.database import transaction

pytestmark = pytest.mark.integration
pytest_plugins = ["test_review_integration"]


def test_base_corpus_choices_submit_and_worker_keep_provisional_labels(console_db, monkeypatch):
    from biosentinelle_vision import commands, console_tasks
    from biosentinelle_vision.training import poc

    root = console_db.output_root
    (root / "classification").mkdir(parents=True)
    (root / "classification/videos.json").write_text(
        json.dumps(
            {
                "class_manifest_version": "v3-10.1",
                "videos": [{"video_id": "one"}, {"video_id": "two"}],
            }
        ),
        encoding="utf-8",
    )
    (root / "training.json").write_text(
        json.dumps(
            {
                "class_manifest_version": "v3-10.1",
                "crops": [{"crop_id": "fixture"}],
            }
        ),
        encoding="utf-8",
    )
    prepare = MagicMock()
    monkeypatch.setattr(poc, "prepare_snapshot", prepare)
    train = MagicMock(return_value={"status": "completed", "checkpoint": "fixture-only"})
    monkeypatch.setattr(commands, "train_from_manifest", train)
    monkeypatch.setattr(
        console_tasks, "register_model", MagicMock(return_value={"model_id": "fixture"})
    )
    with TestClient(app) as client:
        choices = client.get("/console/training/datasets").json()
        assert choices[0]["id"] == "base" and choices[0]["ready"]
        assert choices[0]["video_count"] == 2 and choices[0]["crop_count"] == 1
        response = client.post("/console/training", json={"dataset_id": "base"})
        assert response.status_code == 202, response.text
        identifier = response.json()["id"]
        execute(identifier, console_db, load_classes())
        task = client.get(f"/console/tasks/{identifier}").json()
        assert task["status"] == "completed", task["error"]
    config = train.call_args.args[0]
    assert config.training.allow_filename_labels is True
    assert config.output_root == root
    assert config.train_manifest == root / f"console/datasets/base/{identifier}/training.json"
    assert prepare.call_count == 1


def test_base_corpus_missing_is_disabled_and_cannot_be_queued(console_db):
    with TestClient(app) as client:
        choices = client.get("/console/training/datasets").json()
        assert choices[0]["id"] == "base" and choices[0]["ready"] is False
        assert client.post("/console/training", json={"dataset_id": "base"}).status_code == 422
        assert client.post("/console/training", json={"dataset_id": "unknown"}).status_code == 422
        assert (
            client.post(
                "/console/training", json={"dataset_id": "base", "allow_filename_labels": True}
            ).status_code
            == 422
        )


@pytest.mark.ml
def test_real_cpu_training_from_web_dataset_and_registered_metrics(
    console_db, monkeypatch, tmp_path
):
    torch = pytest.importorskip("torch")
    pytest.importorskip("timm")
    torch.set_num_threads(2)
    from biosentinelle_vision.review.exporting import archive, snapshot
    from biosentinelle_vision.storage import LocalStorage
    from test_review_integration import import_fixture, validate

    from shared import training_metrics
    from shared.review import database, service
    from shared.review.schemas import DatasetRequest

    monkeypatch.setattr(training_metrics, "connect", database.connect)
    classes = load_classes()
    for index, label in enumerate(classes.names):
        imported = import_fixture(console_db, name=f"{label}.mp4", seed=100 + index)
        samples = service.list_samples(None, None, None, 100, 0, imported["video_id"])
        for sample in samples:
            validate(sample, label)
    imported = import_fixture(console_db, name="validation-chevreuil.mp4", split="val", seed=400)
    for sample in service.list_samples(None, None, None, 100, 0, imported["video_id"]):
        validate(sample, "chevreuil")
    version = snapshot(DatasetRequest(name="synthetic-web-training-test"), "test-only", classes)
    archive(version, LocalStorage(console_db.output_root))
    settings = console_db.model_copy(
        update={"checkpoint_root": tmp_path / "checkpoints", "gpu_lock_path": tmp_path / "gpu.lock"}
    )
    with TestClient(app) as client:
        response = client.post(
            "/console/training",
            headers={"X-Reviewer": "test-only"},
            json={
                "dataset_id": version,
                "model_name": "tf_efficientnetv2_b0",
                "image_size": 32,
                "batch_size": 2,
                "accumulation_steps": 1,
                "epochs_head": 1,
                "epochs_finetune": 1,
                "amp": "off",
                "initialization": "scratch",
                "patience": 2,
            },
        )
        assert response.status_code == 202, response.text
        identifier = response.json()["id"]
        execute(identifier, settings, classes)
        task = client.get(f"/console/tasks/{identifier}").json()
        assert task["status"] == "completed", task.get("error")
        assert task["progress"]["current"] == 1
        assert (settings.checkpoint_root / identifier / "last.pt").is_file()
        registered = client.get("/console/models").json()[0]
        assert registered["metadata"]["model_name"] == "tf_efficientnetv2_b0"
        assert registered["metrics"]["validation"]["count"] == 3
        assert registered["active"] is False
        with transaction() as connection:
            metrics = connection.execute(
                "SELECT * FROM training_metrics WHERE run_id=%s", (identifier,)
            ).fetchall()
        assert len(metrics) == 2


@pytest.fixture
def console_db(review_db, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "console_migration", Path("backend/migrations/versions/0004_web_console.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with transaction() as connection:
        monkeypatch.setattr(migration.op, "execute", connection.execute)
        migration.upgrade()
        spec_registry = importlib.util.spec_from_file_location(
            "registry_migration", Path("backend/migrations/versions/0005_classifier_registry.py")
        )
        registry = importlib.util.module_from_spec(spec_registry)
        spec_registry.loader.exec_module(registry)
        monkeypatch.setattr(registry.op, "execute", connection.execute)
        registry.upgrade()
        connection.execute("CREATE TABLE training_runs (LIKE public.training_runs INCLUDING ALL)")
        connection.execute(
            "CREATE TABLE training_metrics (LIKE public.training_metrics INCLUDING ALL)"
        )
    return review_db


def test_chunked_video_import_preview_and_dashboard(console_db):
    from test_review_integration import import_fixture

    import_fixture(console_db)  # Vidéo synthétique lisible ; aucune espèce humainement validée.
    source = (console_db.inbox_root / "chevreuil.mp4").read_bytes()
    headers = {"X-Reviewer": "alice"}
    with TestClient(app) as client:
        assert (
            client.post(
                "/console/uploads", headers=headers, json={"filename": "../x.mp4", "size": 3}
            ).status_code
            == 422
        )
        upload = client.post(
            "/console/uploads",
            headers=headers,
            json={"filename": "chevreuil.mp4", "size": len(source)},
        ).json()
        identifier = upload["id"]
        assert (
            client.post(f"/console/uploads/{identifier}/complete", headers=headers).status_code
            == 409
        )
        assert (
            client.put(
                f"/console/uploads/{identifier}/chunks/0", headers=headers, content=source
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/console/uploads/{identifier}/chunks/0", headers=headers, content=source
            ).status_code
            == 200
        )
        different = b"x" * len(source)
        assert (
            client.put(
                f"/console/uploads/{identifier}/chunks/0", headers=headers, content=different
            ).status_code
            == 409
        )
        operation = client.post(f"/console/uploads/{identifier}/complete", headers=headers).json()
        execute(operation["id"], console_db, load_classes())
        assert client.get(operation["status_url"]).json()["status"] == "completed"
        library = client.get("/console/videos").json()
        uploaded = next(item for item in library if item["id"] == identifier)
        assert uploaded["species_candidate"] == "chevreuil"
        assert uploaded["metadata"]["frames"] == 4
        assert (
            client.get(
                f"/console/videos/{identifier}/file", headers={"Range": "bytes=0-99"}
            ).status_code
            == 206
        )
        counts = client.get("/console/dashboard").json()["counts"]
        assert counts["videos"] == 1 and counts["species"] == 0 and counts["pending"] == 3
        assert (
            client.post(
                f"/console/videos/{identifier}/analyze", headers=headers, json={}
            ).status_code
            == 422
        )
        queued = client.post(
            f"/console/videos/{identifier}/analyze", headers=headers, json={"detection_only": True}
        )
        assert queued.status_code == 202
        assert console.task(queued.json()["id"])["status"] == "queued"


def test_cancellation_outbox_and_idempotence(console_db, monkeypatch):
    from biosentinelle_vision import console_tasks

    task = console.submit("training", {"dataset_id": "not-executed"}, "alice")
    with TestClient(app) as client:
        assert (
            client.post(
                f"/console/tasks/{task['id']}/cancel", headers={"X-Reviewer": "alice"}
            ).status_code
            == 202
        )
        assert console.publish_pending(MagicMock()) == 1
        assert console.publish_pending(MagicMock()) == 0
        perform = MagicMock()
        monkeypatch.setattr(console_tasks, "perform", perform)
        execute(task["id"], console_db, load_classes())
        assert console.task(task["id"])["status"] == "cancelled"
        perform.assert_called_once()  # La fonction vérifie l'arrêt avant toute opération ML.
        execute(task["id"], console_db, load_classes())
        perform.assert_called_once()


def test_cancellation_real_dispatch_never_loads_torch(console_db):
    task = console.submit("training", {"dataset_id": "not-executed"}, "alice")
    with transaction() as connection:
        connection.execute(
            "UPDATE console_tasks SET cancel_requested=true WHERE id=%s", (task["id"],)
        )
    execute(task["id"], console_db, load_classes(), Event())
    assert console.task(task["id"])["status"] == "cancelled"


def test_registry_selection_freezes_checkpoint_for_queued_analysis(console_db):
    from test_review_integration import import_fixture

    imported = import_fixture(console_db)
    model_id = "11111111-1111-4111-8111-111111111111"
    with transaction() as connection:
        connection.execute(
            """INSERT INTO console_models
          (id,name,checkpoint_key,sha256,metadata,metrics,actor,status)
          VALUES(%s,'test-only','test.pt','known-hash','{}','{}','alice','candidate')""",
            (model_id,),
        )
    with TestClient(app) as client:
        headers = {"X-Reviewer": "alice"}
        assert (
            client.post(f"/console/models/{model_id}/activate", headers=headers).status_code == 200
        )
        operation = client.post(
            f"/console/videos/{imported['video_id']}/analyze", headers=headers, json={}
        ).json()
        assert console.task(operation["id"])["request"]["model"]["sha256"] == "known-hash"
        assert client.get("/console/models").json()[0]["active"] is True
        assert (
            client.post(
                "/console/training", headers=headers, json={"dataset_id": "a" * 64}
            ).status_code
            == 422
        )
