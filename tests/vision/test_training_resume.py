import json
import threading
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.config import TrainingConfig, VisionSettings
from biosentinelle_vision.errors import ManifestError, TrainingInterrupted
from biosentinelle_vision.schemas import Box, CropRecord, CropsManifest, FrameRecord
from biosentinelle_vision.storage import LocalStorage
from PIL import Image

pytestmark = pytest.mark.ml


def synthetic_training(
    root: Path, classes: ClassManifest
) -> tuple[VisionSettings, tuple[CropRecord, ...]]:
    storage = LocalStorage(root / "images")
    records, truth = [], {}
    for split in ("train", "val", "test"):
        for index, name in enumerate(classes.names):
            key = f"{split}/{index}.png"
            storage.path(key).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (48, 48), (index * 20, 50, 80)).save(storage.path(key))
            video_id = f"{split}-{index}"
            truth[video_id] = name
            records.append(
                CropRecord(
                    crop_id=video_id,
                    image_key=key,
                    frame=FrameRecord(
                        video_id=video_id,
                        group_id=video_id,
                        frame_index=0,
                        time_seconds=0,
                        image_key=key,
                        split=split,
                    ),
                    box=Box(x=0, y=0, w=1, h=1),
                    detection_confidence=0.9,
                    review="accept",
                    label=name,
                )
            )
    storage.write_json(
        "review.json",
        CropsManifest(class_manifest_version=classes.version, crops=tuple(records)).model_dump(
            mode="json"
        ),
    )
    storage.write_json(
        "video_truth.json",
        {"class_manifest_version": classes.version, "human_validated": True, "video_truth": truth},
    )
    return VisionSettings(
        device="cpu",
        initial_checkpoint=None,
        output_root=storage.root,
        checkpoint_root=root / "checkpoints",
        train_manifest=storage.path("review.json"),
        training=TrainingConfig(
            initialization="scratch",
            model_name="mobilenetv3_small_050",
            image_size=32,
            batch_size=2,
            accumulation_steps=3,
            epochs_head=2,
            epochs_finetune=2,
            video_truth_manifest=storage.path("video_truth.json"),
        ),
    ), tuple(records)


def torch_cpu():
    torch = pytest.importorskip("torch")
    pytest.importorskip("timm")
    torch.set_num_threads(1)
    return torch


def test_resume_restores_optimizer_rng_and_rejects_changed_data(
    tmp_path: Path, classes: ClassManifest, monkeypatch
):
    torch = torch_cpu()
    from biosentinelle_vision.training import engine

    config, records = synthetic_training(tmp_path, classes)
    config.training.run_id = "full"
    full = engine.train(records, LocalStorage(config.output_root), classes, config)
    stop = threading.Event()
    config.training.run_id = "partial"
    original = engine.train_epoch

    def interrupt_after_one(*args):
        loss = original(*args)
        stop.set()
        return loss

    monkeypatch.setattr(engine, "train_epoch", interrupt_after_one)
    with pytest.raises(TrainingInterrupted):
        engine.train(records, LocalStorage(config.output_root), classes, config, stop=stop)
    last = config.checkpoint_root / "partial/last.pt"
    assert torch.load(last, weights_only=True)["epoch"] == 1
    monkeypatch.setattr(engine, "train_epoch", original)
    config.training.resume_checkpoint = last
    resumed = engine.train(records, LocalStorage(config.output_root), classes, config)
    assert len(resumed["history"]) == 4
    a = torch.load(full["checkpoint"], weights_only=True)["state_dict"]
    b = torch.load(resumed["checkpoint"], weights_only=True)["state_dict"]
    assert all(torch.equal(a[key], b[key]) for key in a)
    assert resumed["history"] == full["history"]
    assert (config.output_root / "training/partial/run.json").is_file()
    Image.new("RGB", (48, 48), "red").save(config.output_root / records[0].image_key)
    with pytest.raises(ManifestError, match="modifiés"):
        engine.train(records, LocalStorage(config.output_root), classes, config)


def test_oom_rolls_back_epoch_and_adjusts_effective_batch(
    tmp_path: Path, classes: ClassManifest, monkeypatch
):
    torch = torch_cpu()
    from biosentinelle_vision.training import engine

    config, records = synthetic_training(tmp_path, classes)
    config.training.epochs_head = config.training.epochs_finetune = 1
    config.training.run_id = "oom"
    original, attempts = engine.train_epoch, []

    def fail_once(*args):
        result = original(*args)
        attempts.append(True)
        if len(attempts) == 1:
            raise torch.OutOfMemoryError("Injected test-only OOM after optimizer updates")
        return result

    monkeypatch.setattr(engine, "train_epoch", fail_once)
    result = engine.train(records, LocalStorage(config.output_root), classes, config)
    assert all(
        row["batch_size"] == 1 and row["accumulation_steps"] == 6 for row in result["history"]
    )
    state = torch.load(result["resume_checkpoint"], weights_only=True)
    assert state["oom_events"][0]["previous_batch"] == 2
    monkeypatch.setattr(engine, "train_epoch", original)
    config.training.run_id = "reference"
    config.training.batch_size, config.training.accumulation_steps = 1, 6
    reference = engine.train(records, LocalStorage(config.output_root), classes, config)
    a = torch.load(result["checkpoint"], weights_only=True)["state_dict"]
    b = torch.load(reference["checkpoint"], weights_only=True)["state_dict"]
    assert all(torch.equal(a[key], b[key]) for key in a)


def test_accumulation_normalizes_last_incomplete_group():
    torch = torch_cpu()
    from biosentinelle_vision.training.steps import train_epoch

    torch.manual_seed(10)
    a = torch.nn.Linear(4, 2)
    b = torch.nn.Linear(4, 2)
    b.load_state_dict(a.state_dict())
    data = torch.utils.data.TensorDataset(torch.randn(5, 4), torch.tensor([0, 1, 0, 0, 1]))
    for model, batch, accumulation in ((a, 2, 3), (b, 5, 1)):
        model.get_classifier = lambda model=model: model
        train_epoch(
            model,
            torch.utils.data.DataLoader(data, batch_size=batch),
            torch.optim.SGD(model.parameters(), lr=0.01),
            torch.amp.GradScaler("cuda", enabled=False),
            torch.nn.CrossEntropyLoss(),
            "cpu",
            None,
            accumulation,
            "head",
            threading.Event(),
        )
    assert torch.allclose(a.weight, b.weight, atol=1e-7)


def test_cli_local_training_and_video_evaluation(
    tmp_path: Path, classes: ClassManifest, monkeypatch
):
    torch_cpu()
    from biosentinelle_vision.cli import main

    settings, _ = synthetic_training(tmp_path, classes)
    settings.training.run_id = "cli"
    settings.training.epochs_head = settings.training.epochs_finetune = 1
    path = tmp_path / "config.json"
    path.write_text(settings.model_dump_json(), encoding="utf-8")
    assert main(["train-classifier", "--config", str(path), "--local"]) == 0
    monkeypatch.setenv("BIOSENTINELLE_TRAIN_CONFIG", str(tmp_path / "must-not-be-read.json"))
    assert (
        main(
            [
                "train-classifier",
                "--resume",
                str(settings.checkpoint_root / "cli/last.pt"),
                "--local",
            ]
        )
        == 0
    )
    monkeypatch.delenv("BIOSENTINELLE_TRAIN_CONFIG")
    best = settings.checkpoint_root / "cli/best.pt"
    assert main(["evaluate-classifier", "--config", str(path), "--checkpoint", str(best)]) == 0
    metrics = json.loads((settings.output_root / "classifier_evaluation.json").read_text())
    assert metrics["images"]["count"] == 10 and metrics["videos"]["count"] == 10
    assert len(metrics["images"]["confusion_matrix"]) == 10
