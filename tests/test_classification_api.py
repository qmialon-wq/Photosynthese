from uuid import uuid4

import pytest
from app.main import app
from biosentinelle_vision.classification.contracts import ModelVersion
from fastapi.testclient import TestClient
from test_console import console_db  # noqa: F401

from shared import console
from shared.review.database import jsonb, transaction

pytestmark = pytest.mark.integration
pytest_plugins = ["test_review_integration"]


@pytest.mark.usefixtures("console_db")
def test_benchmark_list_omits_predictions_and_keeps_real_metrics():
    identifier = str(uuid4())
    report = {
        "dataset_version": "test-only",
        "human_validated": False,
        "protocol": {"split": "val"},
        "models": [
            {
                "model": {"model_id": "test-only"},
                "metrics": {"macro_f1": 0.25},
                "predictions": [{"crop_id": "not-in-summary"}],
            }
        ],
    }
    with transaction() as connection:
        connection.execute(
            """INSERT INTO classifier_comparisons(id,report,report_sha256,actor)
            VALUES(%s,%s,'test-only','test')""",
            (identifier, jsonb(report)),
        )
    with TestClient(app) as client:
        response = client.get("/classification/comparisons?limit=1")
        assert response.status_code == 200
        row = response.json()[0]
        assert row["human_validated"] is False and row["models"][0]["metrics"]["macro_f1"] == 0.25
        assert "predictions" not in row["models"][0]
        assert client.get(f"/classification/comparisons/{identifier}").json()["report"] == report


@pytest.mark.usefixtures("console_db")
def test_jobs_are_async_scoped_and_do_not_import_ml():
    with TestClient(app) as client:
        response = client.post(
            "/classification/embeddings/extract", json={"manifest_key": "training.json"}
        )
        assert response.status_code == 202, response.text
        row = console.task(response.json()["id"])
        assert row["status"] == "queued" and row["kind"] == "embeddings_extract"
        assert not row["request"]["allow_weak_labels"]
        for bad in ("../outside.json", "C:/outside.json", "/outside.json"):
            assert (
                client.post(
                    "/classification/embeddings/extract", json={"manifest_key": bad}
                ).status_code
                == 422
            )
        assert (
            client.post(
                "/classification/embeddings/train",
                json={"index_key": "embeddings/datasets/test.json", "candidates": ["unknown"]},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/classification/embeddings/extract",
                json={"manifest_key": "training.json", "batch_size": 100},
            ).status_code
            == 422
        )


@pytest.mark.usefixtures("console_db")
def test_comparison_freezes_registry_versions_and_protects_test(monkeypatch):
    from app import console as routes

    monkeypatch.setattr(routes, "dataset_ready", lambda _: {})
    identifier = str(uuid4())
    with transaction() as connection:
        connection.execute(
            """INSERT INTO console_models
            (id,name,checkpoint_key,sha256,metadata,metrics,actor,family,version)
            VALUES(%s,'candidate','run/model.json',%s,'{}','{}','test','embedding','one')""",
            (identifier, "a" * 64),
        )
    body = {"manifest_key": "training.json", "model_ids": [identifier]}
    with TestClient(app) as client:
        response = client.post("/classification/comparisons", json=body)
        assert response.status_code == 202, response.text
        frozen = console.task(response.json()["id"])["request"]["models"][0]
        version = ModelVersion.model_validate(frozen)
        assert version.classifier_family == "embedding" and version.sha256 == "a" * 64
        for options in ({"split": "test"}, {"split": "test", "confirm_final_test": True}):
            assert (
                client.post("/classification/comparisons", json={**body, **options}).status_code
                == 422
            )
        assert (
            client.post(
                "/classification/comparisons", json={**body, "model_ids": [identifier, identifier]}
            ).status_code
            == 422
        )
        response = client.post(
            f"/classification/models/{identifier}/promote",
            json={"comparison_id": str(uuid4())},
        )
        assert response.status_code == 202
        assert console.task(response.json()["id"])["kind"] == "model_promote"
        response = client.post(
            f"/console/models/{identifier}/evaluate",
            json={"dataset_id": "a" * 64, "split": "val"},
        )
        assert response.status_code == 202, response.text
        assert console.task(response.json()["id"])["request"]["model"]["family"] == "embedding"
        assert (
            client.post(
                f"/console/models/{identifier}/evaluate",
                json={"dataset_id": "a" * 64, "split": "test"},
            ).status_code
            == 422
        )


def test_export_is_confined_to_results(console_db, monkeypatch, tmp_path):  # noqa: F811
    row = {"status": "completed", "kind": "embeddings_cluster", "result": {}}
    monkeypatch.setattr(console, "task", lambda _: row)
    console_db.output_root.mkdir(parents=True)
    export = console_db.output_root / "cluster.json"
    export.write_text('{"schema_version":"test-only"}')
    row["result"]["report"] = str(export)
    with TestClient(app) as client:
        endpoint = f"/classification/tasks/{uuid4()}/artifact"
        assert client.get(endpoint).json() == {"schema_version": "test-only"}
        outside = tmp_path / "outside.json"
        outside.write_text('{"private":true}')
        row["result"]["report"] = str(outside)
        assert client.get(endpoint).status_code == 404
