import os
import subprocess
import sys
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.config import CropsConfig, VisionSettings
from biosentinelle_vision.datasets.crops import build_crops
from biosentinelle_vision.datasets.review import apply_review
from biosentinelle_vision.detection.batch import detect_frames
from biosentinelle_vision.detection.megadetector import MegaDetector
from biosentinelle_vision.errors import ManifestError, ModelError
from biosentinelle_vision.schemas import Box, Detection, FrameRecord, FramesManifest
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.training.dataset import select_samples
from PIL import Image
from pydantic import ValidationError


def test_imports_do_not_load_models_or_touch_disk(tmp_path: Path) -> None:
    code = """
import importlib, pkgutil, sys, socket, urllib.request
def forbidden(*args, **kwargs):
    raise AssertionError('Network forbidden during imports')
socket.create_connection = forbidden
urllib.request.urlopen = forbidden
import biosentinelle_vision
for module in pkgutil.walk_packages(biosentinelle_vision.__path__, 'biosentinelle_vision.'):
    if not module.name.endswith('.__main__'):
        importlib.import_module(module.name)
for name in ('torch', 'torchvision', 'timm', 'megadetector', 'cv2', 'google.colab'):
    assert name not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=tmp_path,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_class_order_and_legacy_checkpoint(classes: ClassManifest) -> None:
    assert classes.names == (
        "chevreuil",
        "sanglier",
        "buse",
        "pigeons",
        "martres",
        "renards",
        "blaireaux",
        "chouette",
        "geai",
        "faisans",
    )
    classes.check_checkpoint({"classes": list(classes.names)})
    with pytest.raises(ManifestError):
        classes.check_checkpoint({"classes": list(reversed(classes.names))})
    with pytest.raises(ManifestError):
        classes.check_checkpoint(
            {"classes": list(classes.names), "class_manifest_version": "other"}
        )


def test_settings_nested_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIOSENTINELLE_VISION_FRAMES__MAX_PER_VIDEO", "7")
    assert VisionSettings().frames.max_per_video == 7
    with pytest.raises(ValidationError):
        VisionSettings(detection_threshold=2)
    with pytest.raises(ValidationError):
        Box(x=0.8, y=0, w=0.4, h=1)


def test_storage_atomic_and_confined(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "storage")
    assert not storage.root.exists()
    storage.write_bytes("a/b.txt", b"first")
    storage.write_bytes("a/b.txt", b"second")
    assert storage.read_bytes("a/b.txt") == b"second"
    assert len(list((storage.root / "a").iterdir())) == 1
    with pytest.raises(ValueError):
        storage.write_bytes("../outside.txt", b"bad")


class DetectorFixture:
    """Uniquement une fixture de contrat, jamais un détecteur du package."""

    identity = "test-fixture"

    def detect(self, image: Image.Image) -> tuple[Detection, ...]:
        if image.getpixel((0, 0))[0] == 0:
            raise ModelError("fixture failure")
        return (Detection(box=Box(x=0, y=0, w=1, h=1), confidence=0.9),)


def test_detection_errors_review_and_training_filter(
    classes: ClassManifest, tmp_path: Path
) -> None:
    storage = LocalStorage(tmp_path)
    storage.path("frames").mkdir()
    Image.new("RGB", (64, 48), "white").save(storage.path("frames/good.png"))
    Image.new("RGB", (64, 48), "black").save(storage.path("frames/bad.png"))
    source = FramesManifest(
        class_manifest_version=classes.version,
        frames=tuple(
            FrameRecord(
                video_id=name,
                group_id=name,
                frame_index=0,
                time_seconds=0,
                image_key=f"frames/{name}.png",
                split="train",
                species_candidate="renards",
            )
            for name in ("good", "bad")
        ),
    )
    detected = detect_frames(source, DetectorFixture(), storage)
    assert detected.frames[0].detections and detected.frames[0].error is None
    assert detected.frames[1].error and not detected.frames[1].detections
    crops = build_crops(detected, storage, CropsConfig())
    assert len(crops) == 1 and crops[0].label is None
    assert not select_samples(crops, classes)
    corrected = Box(x=0.25, y=0, w=0.75, h=1)
    reviewed = apply_review(
        crops,
        crops[0].crop_id,
        accept=True,
        label="buse",
        box=corrected,
        classes=classes,
        storage=storage,
        config=CropsConfig(margin=0),
    )
    assert reviewed[0].frame.split == crops[0].frame.split
    assert reviewed[0].label == "buse" and reviewed[0].box == corrected
    with Image.open(storage.path(reviewed[0].image_key)) as image:
        assert image.size == (48, 48)
    assert select_samples(reviewed, classes) == reviewed
    leaked = reviewed[0].model_copy(
        update={
            "crop_id": "another",
            "frame": reviewed[0].frame.model_copy(update={"split": "val"}),
        }
    )
    with pytest.raises(ManifestError, match="Fuite"):
        select_samples((*reviewed, leaked), classes)
    rejected = apply_review(
        reviewed,
        crops[0].crop_id,
        accept=False,
        label=None,
        box=None,
        classes=classes,
        storage=storage,
        config=CropsConfig(),
    )
    assert not select_samples(rejected, classes)


def test_detector_requires_existing_local_weights(tmp_path: Path) -> None:
    with pytest.raises(ModelError, match="manquants"):
        MegaDetector(tmp_path / "missing.pt", VisionSettings())
