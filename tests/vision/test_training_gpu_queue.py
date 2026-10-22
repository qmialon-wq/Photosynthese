import json
import os
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.training.commands import enqueue_training
from redis import Redis

from shared.vision_jobs import JobStore

from .test_training_resume import synthetic_training

pytestmark = [pytest.mark.gpu, pytest.mark.integration]


@pytest.mark.parametrize("backbone", ["convnext_tiny", "tf_efficientnetv2_b0"])
def test_real_gpu_training_is_serialized_and_persists_metrics(
    classes: ClassManifest, backbone: str
):
    if os.getenv("BIOSENTINELLE_TRAINING_QUEUE_TEST") != "1":
        pytest.skip("Activer explicitement le test de file GPU avec données synthétiques")
    token = "test-" + str(uuid4())
    root = Path("/storage/results/vision/gpu-training-test") / token
    settings, _ = synthetic_training(root, classes)
    settings.device = "cuda"
    settings.checkpoint_root = Path("/storage/checkpoints/gpu-training-test")
    settings.training.run_id = token
    settings.training.model_name = backbone
    settings.training.image_size = 224
    settings.training.batch_size = 2
    settings.training.accumulation_steps = 4
    settings.training.epochs_head = settings.training.epochs_finetune = 1
    settings.training.database_metrics = True
    job = enqueue_training(settings)
    with Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    ) as client:
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            current = JobStore(client).get(job["id"])
            if current["status"] in ("completed", "error"):
                break
            time.sleep(1)
        assert current["status"] == "completed", current
    result = current["result"]
    assert Path(result["checkpoint"]).is_file()
    assert Path(result["resume_checkpoint"]).is_file()
    journal = settings.output_root / "training" / token
    metadata = json.loads((journal / "run.json").read_text())
    assert metadata["device"] == "cuda" and metadata["amp_dtype"] != "None"
    assert json.loads((journal / "database_sync.json").read_text())["status"] == "ok"
    assert result["history"][0]["validation"]["videos"]["count"] == 10
    with urllib.request.urlopen(
        f"http://backend:8000/training/runs/{token}", timeout=5
    ) as response:
        assert json.load(response)["status"] == "completed"
    local_result = {
        "job_id": job["id"],
        "run_id": token,
        "metadata": metadata,
        "best_checkpoint": result["checkpoint"],
        "resume_checkpoint": result["resume_checkpoint"],
    }
    (root / "verification.json").write_text(json.dumps(local_result, indent=2), encoding="utf-8")
