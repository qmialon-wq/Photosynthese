from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from biosentinelle_vision.review.exporting import canonical
from biosentinelle_vision.review.images import blob, quality, render, similar
from biosentinelle_vision.storage import LocalStorage
from PIL import Image
from pydantic import ValidationError

from shared.review.schemas import Box, Decision, ImportVideo
from shared.vision_jobs import JobStore, ReviewRequest


@pytest.mark.parametrize("path", ["../secret.mp4", "/etc/video.mp4", "C:/video.mp4", "a\\b.mp4"])
def test_review_import_confines_paths(path):
    with pytest.raises(ValidationError):
        ImportVideo(video=path)


def test_review_boxes_and_decisions_validate():
    with pytest.raises(ValidationError):
        Box(x=0.9, y=0, w=0.5, h=0.5)
    with pytest.raises(ValidationError):
        Decision(expected_revision=0, decision="reject", label="chevreuil", reason="refus")


def test_quality_detects_blur_size_and_similarity():
    image = Image.new("RGB", (12, 12), "gray")
    descriptor = quality(image)
    assert descriptor["blurry"] and descriptor["too_small"]
    assert similar(descriptor, quality(image.copy()))
    assert not similar(descriptor, quality(Image.new("RGB", (12, 12), "white")))
    noise = Image.fromarray(np.random.default_rng(2).integers(0, 256, (64, 64, 3), dtype=np.uint8))
    assert not quality(noise)["blurry"]


def test_corrected_crop_preserves_original(tmp_path: Path):
    storage = LocalStorage(tmp_path)
    image = Image.fromarray(np.random.default_rng(1).integers(0, 256, (80, 80, 3), dtype=np.uint8))
    buffer = BytesIO()
    image.save(buffer, "JPEG")
    original, digest = blob(storage, buffer.getvalue())
    recipe = {"margin": 0.12, "jpeg_quality": 93}
    first = render(storage, original, {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}, recipe)
    second = render(storage, original, {"x": 0.4, "y": 0.4, "w": 0.5, "h": 0.5}, recipe)
    assert first["crop_key"] != second["crop_key"]
    assert storage.read_bytes(original) == buffer.getvalue()
    assert blob(storage, buffer.getvalue()) == (original, digest)
    assert storage.path(first["crop_key"]).exists()
    storage.write_bytes(original, b"corrupt")
    with pytest.raises(ValueError, match="corrompu"):
        blob(storage, buffer.getvalue())


def test_canonical_and_queue_contract():
    assert canonical({"a": 1, "b": 2}) == canonical({"b": 2, "a": 1})
    redis = MagicMock()
    job = JobStore(redis).enqueue(ReviewRequest(operation_id="operation"))
    assert job["kind"] == "review"
    assert job["request"]["operation_id"] == "operation"
    assert "configuration" not in job["request"]
