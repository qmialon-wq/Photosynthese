from collections.abc import Callable
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.commands import training_samples
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.datasets.inventory import inventory
from biosentinelle_vision.datasets.prepare import prepare_training
from biosentinelle_vision.datasets.review import apply_review
from biosentinelle_vision.datasets.split import split_videos
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.schemas import CropsManifest
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.training.dataset import CropsDataset, select_samples

from .test_make_commands import reviewed_dataset
from .test_video_and_gpu_lock import DetectorFixture


def test_weak_labels_require_opt_in_and_never_become_human(tmp_path: Path, classes: ClassManifest):
    settings, manifest = reviewed_dataset(tmp_path, classes)
    weak = tuple(
        record.model_copy(
            update={
                "review": "pending",
                "label": None,
                "frame": record.frame.model_copy(update={"species_candidate": record.label}),
            }
        )
        for record in manifest.crops
    )
    LocalStorage(tmp_path).write_json(
        "review.json", manifest.model_copy(update={"crops": weak}).model_dump(mode="json")
    )
    with pytest.raises(ManifestError):
        training_samples(settings, classes)
    settings.training.allow_filename_labels = True
    samples = training_samples(settings, classes)
    assert len(samples) == 20
    assert all(r.review == "pending" and r.label == r.frame.species_candidate for r in samples)
    assert all(r.label is None for r in weak)
    dataset = CropsDataset(samples, LocalStorage(tmp_path), classes, lambda im: im.size)
    with pytest.raises(ManifestError):
        dataset[0]
    dataset.allow_filename_labels = True
    assert dataset[0][0] == (48, 48)
    assert select_samples(samples, classes) == ()


def test_human_correction_wins_quota_and_rejection_is_excluded(
    tmp_path: Path, classes: ClassManifest
):
    _, manifest = reviewed_dataset(tmp_path, classes)
    human = manifest.crops[0]
    weak = human.model_copy(
        update={
            "crop_id": "weak",
            "review": "pending",
            "detection_confidence": 1,
            "frame": human.frame.model_copy(update={"species_candidate": classes.names[1]}),
        }
    )
    rejected = weak.model_copy(update={"crop_id": "rejected", "review": "reject"})
    assert select_samples([weak, human, rejected], classes, 1, allow_filename_labels=True) == (
        human,
    )
    assert select_samples([rejected], classes, allow_filename_labels=True) == ()
    unknown = weak.model_copy(
        update={"frame": weak.frame.model_copy(update={"species_candidate": None})}
    )
    assert select_samples([unknown], classes, allow_filename_labels=True) == ()


def test_prepare_extracts_crops_and_preserves_review(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
):
    video = make_video()
    source = split_videos(inventory(video.parent, classes), VisionSettings().split, 42)
    storage = LocalStorage(tmp_path / "output")
    settings = VisionSettings()
    result = prepare_training(source, DetectorFixture(), storage, classes, settings)
    assert result["frames"] > 0 and result["crops"] > 0 and result["errors"] == 0
    assert not storage.path("review.json").exists()
    manifest = CropsManifest.model_validate_json(storage.read_bytes("training.json"))
    assert all(r.review == "pending" and r.label == "renards" for r in manifest.crops)
    assert storage.path(manifest.crops[0].image_key).is_file()
    corrected = apply_review(
        manifest.crops,
        manifest.crops[0].crop_id,
        accept=True,
        label="martres",
        box=None,
        classes=classes,
        storage=storage,
        config=settings.crops,
    )[0]
    rejected = manifest.crops[1].model_copy(update={"review": "reject", "label": None})
    storage.write_json(
        "review.json",
        manifest.model_copy(update={"crops": (corrected, rejected)}).model_dump(mode="json"),
    )
    prepare_training(source, DetectorFixture(), storage, classes, settings)
    updated = CropsManifest.model_validate_json(storage.read_bytes("training.json"))
    assert updated.crops[0] == corrected
    assert updated.crops[0].image_key.startswith("reviewed/")
    assert updated.crops[1] == rejected


def test_provisional_samples_still_reject_split_leakage(tmp_path: Path, classes: ClassManifest):
    _, manifest = reviewed_dataset(tmp_path, classes)
    a, b = manifest.crops[0], manifest.crops[10]
    b = b.model_copy(update={"frame": b.frame.model_copy(update={"group_id": a.frame.group_id})})
    with pytest.raises(ManifestError, match="Fuite"):
        select_samples([a, b], classes, allow_filename_labels=True)
