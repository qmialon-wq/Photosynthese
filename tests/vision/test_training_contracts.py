import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.config import TrainingConfig
from biosentinelle_vision.errors import ManifestError, ModelError
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.training.dataset import select_samples
from biosentinelle_vision.training.detector import (
    DetectorTrainingConfig,
    train_detector,
    validate_detector_dataset,
)
from biosentinelle_vision.training.journal import publish
from PIL import Image

from shared.vision_jobs import JobStore, TrainingRequest

from .test_make_commands import reviewed_dataset


def test_video_leakage_rejected_even_if_group_ids_differ(tmp_path: Path, classes: ClassManifest):
    _, source = reviewed_dataset(tmp_path, classes)
    a, b = source.crops[0], source.crops[10]
    b = b.model_copy(update={"frame": b.frame.model_copy(update={"video_id": a.frame.video_id})})
    with pytest.raises(ManifestError, match="Fuite"):
        select_samples([a, b], classes)


def test_training_configuration_and_queue_are_explicit():
    assert TrainingConfig().allow_filename_labels is False
    assert TrainingConfig().accumulation_steps == 4
    with pytest.raises(ValueError):
        TrainingConfig(accumulation_steps=0)
    with pytest.raises(ValueError):
        TrainingConfig(run_id="../invalid")
    client = MagicMock()
    job = JobStore(client).enqueue(TrainingRequest(configuration={"training": {}}))
    assert job["kind"] == "train_classifier"
    assert job["request"]["configuration"]["training"]["run_id"] == job["id"]


def test_sql_failure_keeps_replayable_json(tmp_path: Path, monkeypatch):
    from shared import training_metrics

    def fail(*args):
        raise RuntimeError("test-only PostgreSQL outage")

    monkeypatch.setattr(training_metrics, "project_run", fail)
    publish(LocalStorage(tmp_path), {"run_id": "test", "status": "running"}, [], True)
    assert json.loads((tmp_path / "database_sync.json").read_text())["status"] == "pending"
    assert json.loads((tmp_path / "run.json").read_text())["run_id"] == "test"


def test_detector_requires_verified_boxes_and_refuses_unsupported_training(tmp_path: Path):
    images = []
    for split in ("train", "val"):
        path = tmp_path / f"{split}.png"
        Image.new("RGB", (32, 32), "white" if split == "train" else "black").save(path)
        images.append(
            {
                "image_key": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "video_id": split,
                "split": split,
                "human_verified": True,
                "boxes": [{"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}],
            }
        )
    manifest = tmp_path / "boxes.json"

    def write():
        manifest.write_text(
            json.dumps(
                {"schema_version": "normalized_boxes_v1", "target": "animal", "images": images}
            ),
            encoding="utf-8",
        )

    write()
    config = DetectorTrainingConfig(
        annotations=manifest, image_root=tmp_path, backend="ultralytics"
    )
    assert validate_detector_dataset(config)["boxes"] == 2
    with pytest.raises(ModelError, match="Fine-tuning indisponible"):
        train_detector(config)
    images[0]["human_verified"] = False
    write()
    with pytest.raises(ValueError):
        validate_detector_dataset(config)
    images[0]["human_verified"] = True
    images[0]["boxes"] = []
    write()
    with pytest.raises(ManifestError, match="bounding box"):
        validate_detector_dataset(config)
