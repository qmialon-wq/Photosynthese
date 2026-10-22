from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from shared.vision_jobs import AnalysisRequest, JobStore


def test_enqueue_local_video_and_read_status(tmp_path: Path, monkeypatch):
    inbox = tmp_path / "datasets/inbox"
    inbox.mkdir(parents=True)
    (inbox / "video.mp4").write_bytes(b"not-decoded-in-http")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    with TestClient(app) as client:
        redis = MagicMock()
        app.state.redis = redis
        response = client.post("/vision/analyses", json={"video": "video.mp4"})
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        redis.pipeline.return_value.__enter__.return_value.xadd.assert_called_once()
        redis.get.return_value = response.text
        assert client.get(body["status_url"]).json()["id"] == body["id"]
        assert client.get(body["status_url"] + "/artifacts/video").status_code == 409
        redis.get.return_value = None
        assert client.get(body["status_url"]).status_code == 404
        redis.pipeline.side_effect = ConnectionError("test-disconnected")
        assert client.post("/vision/analyses", json={"video": "video.mp4"}).status_code == 503


@pytest.mark.parametrize(
    "video", ["../video.mp4", "/tmp/video.mp4", "C:/video.mp4", "..\\video.mp4"]
)
def test_paths_are_confined(video):
    with TestClient(app) as client:
        assert client.post("/vision/analyses", json={"video": video}).status_code == 422


def test_missing_video_and_artifact_confinement(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    with TestClient(app) as client:
        assert client.post("/vision/analyses", json={"video": "absent.mp4"}).status_code == 404
        job_id = str(uuid4())
        job = {"id": job_id, "status": "completed", "result": {"output": "../../.."}}
        monkeypatch.setattr(JobStore, "get", lambda *_: job)
        assert client.get(f"/vision/analyses/{job_id}/artifacts/report").status_code == 404


def test_threshold_validation():
    assert AnalysisRequest(video="video.mp4").track_threshold == 0.60
    with pytest.raises(ValueError):
        AnalysisRequest(video="video.mp4", detection_threshold=float("nan"))
