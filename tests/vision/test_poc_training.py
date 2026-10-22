from unittest.mock import Mock

import pytest
from biosentinelle_vision import commands, console_tasks, job_worker
from biosentinelle_vision.config import TrainingConfig, VisionSettings
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.schemas import CropsManifest, Inventory, VideoRecord
from biosentinelle_vision.training.poc import merge_reviews

from shared import console
from shared.vision_jobs import TrainingRequest

from .test_make_commands import reviewed_dataset


def test_reviews_replace_provisional_crops_without_moving_original_test(tmp_path, classes):
    _, source = reviewed_dataset(tmp_path, classes)
    crop = source.crops[0]
    frame = crop.frame.model_copy(update={"split": "test"})
    crop = crop.model_copy(update={"review": "pending", "label": None, "frame": frame})
    manifest = CropsManifest(class_manifest_version=classes.version, crops=(crop,))
    inventory = Inventory(
        class_manifest_version=classes.version,
        dataset_root="unused",
        videos=(
            VideoRecord(
                video_id=frame.video_id, relative_path="v.mp4", content_hash="hash", split="test"
            ),
        ),
    )
    row = {
        "video_id": "hash",
        "id": "human",
        "revision": 2,
        "state": "corrected",
        "split": "train",
        "test_locked": False,
        "render_status": "ready",
        "crop_key": "new.jpg",
        "label": "renards",
        "detection_score": 0.9,
        "box": crop.box.model_dump(),
        "frame_index": 0,
        "time_seconds": 0,
        "original_image_key": "original.jpg",
    }
    merged, audit = merge_reviews(manifest, inventory, [row])
    assert len(merged.crops) == 1
    assert merged.crops[0].review == "accept" and merged.crops[0].label == "renards"
    assert merged.crops[0].frame.split == "test"
    assert merged.crops[0].image_key == "new.jpg"
    assert audit["human_revisions"][0]["effective_split"] == "test"
    rejected, _ = merge_reviews(manifest, inventory, [{**row, "state": "rejected"}])
    assert not rejected.crops
    with pytest.raises(ManifestError, match="rendu"):
        merge_reviews(manifest, inventory, [{**row, "render_status": "pending"}])
    frozen, _ = merge_reviews(
        manifest.model_copy(
            update={
                "crops": (
                    crop.model_copy(update={"frame": frame.model_copy(update={"split": "train"})}),
                )
            }
        ),
        inventory.model_copy(
            update={"videos": (inventory.videos[0].model_copy(update={"split": "train"}),)}
        ),
        [{**row, "test_locked": True}],
    )
    assert frozen.crops[0].frame.split == "test"


def test_unreviewed_crops_keep_their_state_and_duplicate_video_splits_fail(tmp_path, classes):
    _, manifest = reviewed_dataset(tmp_path, classes)
    inventory = Inventory(
        class_manifest_version=classes.version,
        dataset_root="unused",
        videos=tuple(
            VideoRecord(
                video_id=c.frame.video_id,
                relative_path=f"{c.crop_id}.mp4",
                content_hash=c.crop_id,
                split=c.frame.split,
            )
            for c in manifest.crops
        ),
    )
    merged, _ = merge_reviews(manifest, inventory, [])
    assert merged.crops == manifest.crops
    duplicate = inventory.videos[0].model_copy(update={"video_id": "copy", "split": "val"})
    with pytest.raises(ManifestError, match="plusieurs ensembles"):
        merge_reviews(
            manifest, inventory.model_copy(update={"videos": (*inventory.videos, duplicate)}), []
        )


@pytest.mark.parametrize("completed", [True, False])
def test_worker_registers_and_activates_only_after_success(
    tmp_path, classes, monkeypatch, completed
):
    config = VisionSettings(
        output_root=tmp_path,
        checkpoint_root=tmp_path / "checkpoints",
        training=TrainingConfig(run_id="poc", register_model_name="POC", activate_on_success=True),
    )
    train = Mock(return_value={"status": "completed" if completed else "interrupted"})
    register = Mock(return_value={"model_id": "new"})
    activate = Mock(return_value={"active": True, "previous_model_ids": ["old"]})
    monkeypatch.setattr(commands, "train_from_manifest", train)
    monkeypatch.setattr(console_tasks, "register_model", register)
    monkeypatch.setattr(console, "activate_model", activate)
    result = job_worker.execute_job(
        {
            "id": "job",
            "kind": "train_classifier",
            "request": TrainingRequest(configuration=config.model_dump(mode="json")).model_dump(),
        },
        config,
        classes,
    )
    assert register.call_count == int(completed)
    assert activate.call_count == 0
    if completed:
        assert register.call_args.args[0]["checkpoint_key"] == "poc/best.pt"
        assert result["activation"]["active"] is False
        assert (tmp_path / "training/poc/registration.json").is_file()


def test_activation_requires_explicit_registration():
    with pytest.raises(ValueError, match="register_model_name"):
        TrainingConfig(activate_on_success=True)
    assert TrainingConfig().activate_on_success is False
