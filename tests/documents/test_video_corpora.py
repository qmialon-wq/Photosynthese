import json
from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared import console
from shared.documents import service as documents
from shared.parcels import corpora, service
from workers.documents import parcels
from workers.documents.runtime import execute

pytestmark = pytest.mark.integration
PROFILE = {"area_m2": 2500, "land_type": "pasture", "project_type": "housing"}


def video(tmp_path, monkeypatch, *, sha=None, status=None, score=0.9):
    from shared.review.database import jsonb

    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    identifier = str(uuid4())
    with documents.transaction() as connection:
        connection.execute(
            """INSERT INTO console_videos
            (id,filename,video_key,sha256,metadata) VALUES(%s,%s,%s,%s,'{}')""",
            (identifier, f"{identifier}.mp4", f"inbox/{identifier}.mp4", sha or identifier),
        )
    task = None
    if status:
        task = console.submit("analysis", {"video_id": identifier}, "alice")["id"]
        with documents.transaction() as connection:
            connection.execute(
                "UPDATE console_tasks SET status=%s,result=%s WHERE id=%s",
                (status, jsonb({"output": identifier}), task),
            )
    target = tmp_path / "results/vision" / identifier / "report.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "frames_decoded": 10,
                "detections": 1,
                "status": "completed",
                "frames": [
                    {
                        "detections": [
                            {
                                "state": "species_recognized",
                                "classification": {"label": "renards", "score": score},
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return identifier, task


def save_and_submit(client, ids):
    created = client.post("/parcels/corpora", json={"video_ids": ids})
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    saved = client.put(f"/parcels/corpora/{identifier}/profile", json=PROFILE)
    assert saved.status_code == 200, saved.text
    submitted = client.post(f"/parcels/corpora/{identifier}/dossiers", json={"profile_revision": 1})
    assert submitted.status_code == 202, submitted.text
    return identifier, submitted.json()["id"]


def test_corpus_deduplicates_originals_and_validates_all_members(
    document_db, tmp_path, monkeypatch
):
    first, _ = video(tmp_path, monkeypatch, sha="same-sha")
    alias, _ = video(tmp_path, monkeypatch, sha="same-sha")
    with TestClient(app) as client:
        assert client.post("/parcels/corpora", json={"video_ids": []}).status_code == 422
        assert (
            client.post("/parcels/corpora", json={"video_ids": [first, "unknown"]}).status_code
            == 404
        )
        assert client.get("/parcels/corpora").json() == []
        created = client.post("/parcels/corpora", json={"video_ids": [first, first, alias]}).json()
        assert len(created["videos"]) == 1
        assert client.get("/parcels/corpora").json()[0]["video_count"] == 1


def test_completed_analysis_reused_and_only_missing_video_enqueued(
    document_db, tmp_path, monkeypatch
):
    first, completed = video(tmp_path, monkeypatch, status="completed")
    second, _ = video(tmp_path, monkeypatch)
    with TestClient(app) as client:
        identifier, dossier_id = save_and_submit(client, [first, second])
        row = service.dossier(dossier_id)
        assert row["video_count"] == 2 and row["completed_video_count"] == 1
        assert str(row["videos"][0]["analysis_id"]) == completed
        missing = console.task(str(row["videos"][1]["analysis_id"]))
        assert missing["status"] == "queued" and missing["request"]["detection_only"] is True
        assert missing["request"]["infer_every_n_frames"] == 2
        repeated = client.post(
            f"/parcels/corpora/{identifier}/dossiers", json={"profile_revision": 1}
        )
        assert repeated.json()["id"] == dossier_id
        assert service.schedule() == 0
        with documents.transaction() as connection:
            assert (
                connection.execute("SELECT count(*) AS n FROM console_tasks").fetchone()["n"] == 2
            )


def test_wait_for_entire_corpus_then_export_one_snapshot(document_db, tmp_path, monkeypatch):
    first, _ = video(tmp_path, monkeypatch, status="completed", score=0.8)
    second, pending = video(tmp_path, monkeypatch, status="running", score=0.95)
    monkeypatch.setattr(
        parcels.embeddings, "load", lambda *_: (_ for _ in ()).throw(ValueError("missing"))
    )
    with TestClient(app) as client:
        identifier, dossier_id = save_and_submit(client, [first, second])
        assert service.schedule() == 0
        with documents.transaction() as connection:
            connection.execute(
                "UPDATE console_tasks SET status='completed' WHERE id=%s", (pending,)
            )
        assert service.schedule() == 1 and service.schedule() == 0
        task = str(service.dossier(dossier_id)["task_id"])
        assert execute(task, document_db)
        row = client.get(f"/parcels/corpora/{identifier}").json()["dossier"]
        assert row["status"] == "completed", documents.task(task)["error"]
        result = row["result"]
        assert result["video_count"] == 2 and result["frames_decoded"] == 20
        assert len(result["predicted_species"]) == 1 and result["confirmed_species"] == []
        assert result["predicted_species"][0]["score"] == 0.95
        assert {v["video_id"] for v in result["videos"]} == {first, second}
        exported = client.get(f"/parcels/dossiers/{dossier_id}/export")
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("text/plain")
        assert exported.headers["content-disposition"] == (
            f'attachment; filename="dossier-parcelle-{dossier_id}.txt"'
        )
        assert "2 vidéo" in exported.text and first in exported.text and second in exported.text
        assert "décompte d'individus" in exported.text
        assert len({v["report_sha256"] for v in result["videos"]}) == 2
        assert client.get(f"/parcels/dossiers/{dossier_id}/export?format=json").json() == result


def test_failure_is_explicit_retry_preserves_successful_work(document_db, tmp_path, monkeypatch):
    first, completed = video(tmp_path, monkeypatch, status="completed")
    second, running = video(tmp_path, monkeypatch, status="running")
    with TestClient(app) as client:
        identifier, dossier_id = save_and_submit(client, [first, second])
        with documents.transaction() as connection:
            connection.execute("UPDATE console_tasks SET status='error' WHERE id=%s", (running,))
        assert service.schedule() == 0
        assert service.dossier(dossier_id)["status"] == "error"
        assert client.get(f"/parcels/dossiers/{dossier_id}/export").status_code == 409
        retried = client.post(
            f"/parcels/corpora/{identifier}/dossiers", json={"profile_revision": 1}
        )
        assert retried.json()["id"] != dossier_id
        entries = service.dossier(retried.json()["id"])["videos"]
        assert str(entries[0]["analysis_id"]) == completed
        assert str(entries[1]["analysis_id"]) != running
        assert entries[1]["analysis_status"] == "queued"


def test_profile_revisions_and_corpus_members_are_preserved(document_db, tmp_path, monkeypatch):
    first, _ = video(tmp_path, monkeypatch, status="completed")
    with TestClient(app) as client:
        identifier, dossier_id = save_and_submit(client, [first])
        assert (
            client.put(
                f"/parcels/corpora/{identifier}/profile", json={**PROFILE, "area_m2": 1000}
            ).status_code
            == 409
        )
        updated = client.put(
            f"/parcels/corpora/{identifier}/profile",
            json={**PROFILE, "area_m2": 1000, "expected_revision": 1},
        )
        assert updated.json()["revision"] == 2
        assert corpora.read(identifier)["profile"]["profile"]["area_m2"] == 1000
        assert service.dossier(dossier_id)["profile"]["area_m2"] == 2500


def test_active_model_snapshot_and_bulk_import_polling(document_db, tmp_path, monkeypatch):
    first, _ = video(tmp_path, monkeypatch)
    model_id = str(uuid4())
    with documents.transaction() as connection:
        connection.execute(
            """INSERT INTO console_models
            (id,name,checkpoint_key,sha256,metadata,metrics,active,status,actor,version)
            VALUES(%s,'Test-only model','fixture.pt','test-sha',
                   '{}','{}',true,'active','alice','v1')""",
            (model_id,),
        )
    with TestClient(app) as client:
        _, dossier_id = save_and_submit(client, [first])
        task = console.task(str(service.dossier(dossier_id)["videos"][0]["analysis_id"]))
        assert task["request"]["model"]["id"] == model_id
        assert task["request"]["detection_only"] is False
        uploaded = console.submit("import_upload", {"upload_id": str(uuid4())}, "alice")["id"]
        status = client.post(
            "/parcels/import-status", json={"task_ids": [uploaded, str(task["id"])]}
        )
        assert status.status_code == 200 and len(status.json()) == 1
        assert status.json()[0]["id"] == uploaded
