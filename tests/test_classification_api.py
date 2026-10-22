from uuid import uuid4

import pytest
from app.main import app
from biosentinelle_vision.classification.contracts import ModelVersion
from fastapi.testclient import TestClient
from test_console import console_db  # noqa: F401

from shared import console
from shared.review.database import transaction

pytestmark = pytest.mark.integration
pytest_plugins = ["test_review_integration"]


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
def test_comparison_freezes_registry_versions_and_protects_test():
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
