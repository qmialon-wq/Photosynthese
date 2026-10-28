from unittest.mock import MagicMock

import pytest
from biosentinelle_vision import job_worker
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.errors import GpuBusyError, ModelError

from shared.vision_jobs import JobStore


@pytest.mark.parametrize("outcome", ["completed", "busy", "error"])
def test_worker_acknowledges_after_result_and_retries_gpu_busy(monkeypatch, classes, outcome):
    client = MagicMock()
    monkeypatch.setattr(job_worker, "next_message", lambda *_: ("1-0", {"id": "job"}))
    client.xreadgroup.return_value = [("stream", [("1-0", {"id": "job"})])]
    job = {"id": "job", "status": "queued", "request": {"video": "video.mp4"}}
    monkeypatch.setattr(JobStore, "get", lambda *_: job)
    finish = MagicMock()
    monkeypatch.setattr(JobStore, "finish", finish)

    def execute(*args):
        if outcome == "busy":
            raise GpuBusyError("busy")
        if outcome == "error":
            raise ModelError("Poids incompatibles")
        return {"status": "completed", "output": "analyses/test"}

    monkeypatch.setattr(job_worker, "execute_job", execute)
    assert job_worker.consume_one(client, VisionSettings(), classes) is (outcome != "busy")
    if outcome == "busy":
        finish.assert_not_called()
        assert job["status"] == "queued"
    else:
        finish.assert_called_once()
        assert job["status"] == outcome
        if outcome == "error":
            assert "Poids incompatibles" in job["error"]
