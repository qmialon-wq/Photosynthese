from collections.abc import Callable, Sequence
from pathlib import Path

import cv2
import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.classification.model import prediction_from_probabilities
from biosentinelle_vision.config import TrackingConfig, VisionSettings
from biosentinelle_vision.errors import ModelError, VideoError
from biosentinelle_vision.inference.video import analyze_video
from biosentinelle_vision.schemas import Box, Detection, Prediction
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.storage.gpu import exclusive_gpu
from biosentinelle_vision.tracking.iou import IoUTracker
from PIL.Image import Image


class DetectorFixture:
    identity = "synthetic-test-only"

    def detect(self, image: Image) -> tuple[Detection, ...]:
        return (Detection(box=Box(x=0, y=0, w=1, h=1), confidence=0.9),)


class ClassifierFixture:
    def __init__(self, classes: ClassManifest) -> None:
        self.manifest = classes
        self.classes = classes.names

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]:
        return tuple(
            prediction_from_probabilities([1.0] + [0.0] * 9, self.manifest, 0.48) for _ in images
        )


def test_streaming_video_export_with_contract_fixtures(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
) -> None:
    video = make_video()
    storage = LocalStorage(tmp_path / "output")
    report = analyze_video(
        video,
        DetectorFixture(),
        ClassifierFixture(classes),
        IoUTracker(classes, TrackingConfig()),
        classes,
        storage,
        VisionSettings(),
    )
    assert report["frames_decoded"] == 20
    assert report["detections"] == 10
    assert len(report["tracks"]) == 1
    assert report["species"][0]["estimated_tracks"] == 1
    cap = cv2.VideoCapture(str(storage.path(report["annotated_key"])))
    try:
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 20
    finally:
        cap.release()
    assert storage.path("video_report.json").is_file()


def test_video_error_never_generates_success_report(tmp_path: Path, classes: ClassManifest) -> None:
    video = tmp_path / "broken.mp4"
    video.write_bytes(b"bad")
    storage = LocalStorage(tmp_path / "out")
    with pytest.raises(VideoError):
        analyze_video(
            video,
            DetectorFixture(),
            ClassifierFixture(classes),
            IoUTracker(classes, TrackingConfig()),
            classes,
            storage,
            VisionSettings(),
        )
    assert not storage.path("video_report.json").exists()
    assert not storage.path("annotated/video.mp4").exists()


def test_gpu_lock_is_exclusive_without_using_cuda(tmp_path: Path) -> None:
    path = tmp_path / ".gpu.lock"
    with exclusive_gpu("cuda", path):
        with pytest.raises(ModelError, match="déjà active"):
            with exclusive_gpu("cuda", path):
                pytest.fail("Le second verrou aurait dû échouer")
    with exclusive_gpu("cuda", path):
        pass
    assert not (tmp_path / "unused").exists()
    with exclusive_gpu("cpu", tmp_path / "unused/lock"):
        pass
    assert not (tmp_path / "unused").exists()
