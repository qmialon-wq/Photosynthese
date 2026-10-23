import json
from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared.documents import service as documents
from shared.parcels import service
from shared.review.database import jsonb
from workers.documents import parcels
from workers.documents.runtime import execute

pytestmark = pytest.mark.integration


def video_and_analysis(tmp_path, monkeypatch, *, status="completed", frames=None):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    video_id, analysis_id = str(uuid4()), str(uuid4())
    with documents.transaction() as connection:
        connection.execute(
            """INSERT INTO console_videos
            (id,filename,video_key,sha256,metadata)
            VALUES(%s,'terrain.mp4','inbox/video.mp4',%s,'{}')""",
            (video_id, "a" * 64),
        )
        connection.execute(
            """INSERT INTO console_tasks(id,kind,actor,request,status,result)
            VALUES(%s,'analysis','alice',%s,%s,%s)""",
            (analysis_id, jsonb({"video_id": video_id}), status, jsonb({"output": "test-video"})),
        )
    target = tmp_path / "results/vision/test-video/report.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "status": "completed",
                "frames_decoded": 20,
                "detections": sum(len(f["detections"]) for f in frames or []),
                "frames": frames or [],
            }
        ),
        encoding="utf-8",
    )
    return video_id, analysis_id


def save_profile(client, video):
    response = client.put(
        f"/parcels/videos/{video}",
        json={
            "area_m2": 2500,
            "land_type": "pasture",
            "project_type": "housing",
            "locality": "Caen",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_profile_conflict_and_atomic_analysis_submission(document_db, tmp_path, monkeypatch):
    video, _ = video_and_analysis(tmp_path, monkeypatch)
    with TestClient(app) as client:
        profile = save_profile(client, video)
        assert profile["revision"] == 1
        assert (
            client.get(f"/parcels/videos/{video}").json()["profile"]["profile"]["area_m2"] == 2500
        )
        assert (
            client.put(
                f"/parcels/videos/{video}",
                json={**profile["profile"], "area_m2": 1000, "expected_revision": 0},
            ).status_code
            == 409
        )
        invalid = client.post(
            f"/console/videos/{video}/analyze", json={"detection_only": True, "parcel_revision": 99}
        )
        assert invalid.status_code == 422
        with documents.transaction() as connection:
            assert (
                connection.execute("SELECT count(*) AS n FROM console_tasks").fetchone()["n"] == 1
            )
        response = client.post(
            f"/console/videos/{video}/analyze", json={"detection_only": True, "parcel_revision": 1}
        )
        assert response.status_code == 202
        row = client.get(f"/parcels/videos/{video}").json()["dossier"]
        assert row["status"] == "waiting_analysis" and row["analysis_id"] == response.json()["id"]


def test_scheduler_browser_independent_idempotent_and_exports(document_db, tmp_path, monkeypatch):
    video, analysis = video_and_analysis(tmp_path, monkeypatch, status="running")
    with TestClient(app) as client:
        save_profile(client, video)
        first = client.post(
            f"/parcels/videos/{video}/dossiers",
            json={"analysis_id": analysis, "profile_revision": 1},
        ).json()
        again = client.post(
            f"/parcels/videos/{video}/dossiers",
            json={"analysis_id": analysis, "profile_revision": 1},
        ).json()
        assert first["id"] == again["id"]
        assert service.schedule() == 0
        with documents.transaction() as connection:
            connection.execute(
                "UPDATE console_tasks SET status='completed' WHERE id=%s", (analysis,)
            )
        assert service.schedule() == 1 and service.schedule() == 0
        dossier = service.dossier(first["id"])
        monkeypatch.setattr(
            parcels.embeddings, "load", lambda *_: (_ for _ in ()).throw(ValueError("missing"))
        )
        # No fake production model: the actual PostgreSQL lexical retrieval sees an empty corpus.
        assert execute(str(dossier["task_id"]), document_db)
        status = documents.task(str(dossier["task_id"]))
        assert status["status"] == "completed", status["error"]
        persisted = client.get(f"/parcels/videos/{video}?analysis_id={analysis}").json()["dossier"]
        assert persisted["status"] == "completed"
        result = persisted["result"]
        assert result["status"] == "insufficient_sources" and result["sources"] == []
        assert result["green_space"]["recommended_percent"] is None
        assert "absence" in result["observation_summary"]
        assert client.get(f"/parcels/dossiers/{first['id']}/export").status_code == 200
        assert "Votre parcelle" in client.get(f"/parcels/dossiers/{first['id']}/export").text
        assert client.get(f"/parcels/dossiers/{first['id']}/export?format=json").json() == result
        assert client.get(
            f"/parcels/dossiers/{first['id']}/export?format=markdown"
        ).text.startswith("#")


def test_failed_analysis_and_cross_video_are_explicit(document_db, tmp_path, monkeypatch):
    video, analysis = video_and_analysis(tmp_path, monkeypatch, status="running")
    with TestClient(app) as client:
        save_profile(client, video)
        request = client.post(
            f"/parcels/videos/{video}/dossiers",
            json={"analysis_id": analysis, "profile_revision": 1},
        ).json()
        with documents.transaction() as connection:
            connection.execute("UPDATE console_tasks SET status='error' WHERE id=%s", (analysis,))
        service.schedule()
        assert service.dossier(request["id"])["status"] == "error"
        assert client.get(f"/parcels/dossiers/{request['id']}/export").status_code == 409
        assert (
            client.post(
                f"/parcels/videos/{video}/dossiers",
                json={"analysis_id": str(uuid4()), "profile_revision": 1},
            ).status_code
            == 422
        )


def test_predictions_are_hypotheses_and_low_confidence_is_excluded(
    document_db, tmp_path, monkeypatch
):
    frames = [
        {
            "detections": [
                {
                    "state": "species_uncertain",
                    "classification": {"label": "blaireaux", "score": 0.2},
                },
                {
                    "state": "species_recognized",
                    "classification": {"label": "renards", "score": 0.95},
                },
                {"state": "detection_unclassified"},
            ]
        }
    ]
    video, analysis = video_and_analysis(tmp_path, monkeypatch, frames=frames)
    result = parcels.evidence_context(video, analysis)
    assert result["confirmed_species"] == []
    assert [p["name"] for p in result["predicted_species"]] == ["renards"]
    assert result["uncertain_detections"] == 1 and result["unclassified_detections"] == 1


def test_dossier_uses_only_real_approved_citations(document_db, tmp_path, monkeypatch):
    from .test_rag import publication

    _, chunk = publication("We recommend preserving hedgerows in agricultural landscapes.")
    video, analysis = video_and_analysis(tmp_path, monkeypatch)
    monkeypatch.setattr(
        parcels.embeddings, "load", lambda *_: (_ for _ in ()).throw(ValueError("missing"))
    )
    with TestClient(app) as client:
        save_profile(client, video)
        row = client.post(
            f"/parcels/videos/{video}/dossiers",
            json={"analysis_id": analysis, "profile_revision": 1},
        ).json()
        service.schedule()
        task_id = str(service.dossier(row["id"])["task_id"])
        assert execute(task_id, document_db)
        final = service.dossier(row["id"])
        assert final["status"] == "completed", documents.task(task_id)["error"]
        result = final["result"]
        assert result["sources"][0]["chunk_id"] == chunk
        card = result["recommendations"][0]
        assert card["citation"] == result["sources"][0]["citation"]
        assert card["evidence_quote"] in result["sources"][0]["text"]
        assert card["species_conditional"] is True


def test_human_confirmation_matches_console_video_by_hash(document_db, tmp_path, monkeypatch):
    video, analysis = video_and_analysis(tmp_path, monkeypatch)
    review_video = "a" * 64
    with documents.transaction() as connection:
        connection.execute("INSERT INTO review_groups(id,split) VALUES('g','train')")
        connection.execute(
            """INSERT INTO review_videos
            (id,group_id,source_key,original_name,candidates)
            VALUES(%s,'g','source.mp4','source.mp4','[]')""",
            (review_video,),
        )
        connection.execute(
            """INSERT INTO review_frames
            (id,video_id,frame_index,time_seconds,image_key,sha256,width,height,quality)
            VALUES('f',%s,0,0,'frame.jpg','hash',100,100,'{}')""",
            (review_video,),
        )
        connection.execute("""INSERT INTO review_samples(id,frame_id,original_box,
            original_crop_key,detector_identity,detection_score,predicted_label,classification_score)
            VALUES('s','f','{}','crop.jpg','md',0.9,'renards',0.1)""")
        connection.execute("""INSERT INTO review_revisions(sample_id,revision,state,label,box,
            recipe,render_status,actor,provenance)
            VALUES('s',0,'validated','renards','{}','{}','ready','alice','{}')""")
    context = parcels.evidence_context(video, analysis)
    assert context["confirmed_species"][0]["name"] == "renards"
    assert context["observations"][0]["validator"] == "alice"
    assert len(service.snapshot_sha(context)) == 64  # SQL timestamps remain portable.


def test_failed_document_task_can_be_retried(document_db, tmp_path, monkeypatch):
    video, analysis = video_and_analysis(tmp_path, monkeypatch)
    with TestClient(app) as client:
        save_profile(client, video)
        body = {"analysis_id": analysis, "profile_revision": 1}
        first = client.post(f"/parcels/videos/{video}/dossiers", json=body).json()
        service.schedule()
        task = service.dossier(first["id"])["task_id"]
        with documents.transaction() as connection:
            connection.execute(
                "UPDATE document_tasks SET status='error',error='fixture' WHERE id=%s", (task,)
            )
        assert service.dossier(first["id"])["status"] == "error"
        retried = client.post(f"/parcels/videos/{video}/dossiers", json=body).json()
        assert retried["id"] != first["id"]
        assert service.schedule() == 1
