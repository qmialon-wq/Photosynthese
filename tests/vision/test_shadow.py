from unittest.mock import Mock

from biosentinelle_vision.classification.model import prediction_from_probabilities
from biosentinelle_vision.config import TrackingConfig, VisionSettings
from biosentinelle_vision.inference.video import analyze_video
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.tracking.iou import IoUTracker

from .test_video_and_gpu_lock import ClassifierFixture, DetectorFixture


def test_shadow_uses_same_crops_without_changing_primary_or_detector_calls(
    make_video, tmp_path, classes
):
    detector = DetectorFixture()
    detector.detect = Mock(wraps=detector.detect)
    primary = ClassifierFixture(classes)
    shadow = ClassifierFixture(classes)
    shadow.predict = Mock(
        side_effect=lambda images: tuple(
            prediction_from_probabilities([0, 1] + [0] * 8, classes, 0.48) for _ in images
        )
    )
    report = analyze_video(
        make_video(),
        detector,
        primary,
        IoUTracker(classes, TrackingConfig()),
        classes,
        LocalStorage(tmp_path / "out"),
        VisionSettings(infer_every_n_frames=2),
        shadow_classifier=shadow,
    )
    assert detector.detect.call_count == 10 and shadow.predict.call_count == 10
    assert report["tracks"][0]["label"] == "chevreuil"
    assert report["frames"][0]["shadow_predictions"][0]["label"] == "sanglier"
    assert report["diagnostics"]["predictions"] == 10


def test_shadow_failure_does_not_fail_primary_analysis(make_video, tmp_path, classes):
    shadow = ClassifierFixture(classes)
    shadow.predict = Mock(side_effect=RuntimeError("shadow test failure"))
    report = analyze_video(
        make_video(),
        DetectorFixture(),
        ClassifierFixture(classes),
        IoUTracker(classes, TrackingConfig()),
        classes,
        LocalStorage(tmp_path / "out"),
        VisionSettings(),
        shadow_classifier=shadow,
    )
    assert report["status"] == "species_recognized"
    assert "shadow test failure" in report["diagnostics"]["shadow_error"]
    assert shadow.predict.call_count == 1
