from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.classification.model import prediction_from_probabilities
from biosentinelle_vision.config import TrackingConfig, VisionSettings
from biosentinelle_vision.inference.video import analyze_video
from biosentinelle_vision.schemas import Box, Detection, Prediction
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.tracking.base import Observation
from biosentinelle_vision.tracking.iou import IoUTracker
from PIL.Image import Image


class DetectorCase:
    identity = "test-fixture-only"

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def detect(self, image: Image) -> tuple[Detection, ...]:
        if self.mode == "empty":
            return ()
        side = 0.01 if self.mode == "tiny" else 1.0
        return (Detection(box=Box(x=0, y=0, w=side, h=side), confidence=0.83),)


class ClassifierCase:
    def __init__(self, classes: ClassManifest, uncertain: bool) -> None:
        self.classes = classes.names
        self.manifest = classes
        self.uncertain = uncertain

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]:
        if not images:
            pytest.fail("Un lot vide ne doit pas être envoyé au modèle")
        values = [0.1] * 10 if self.uncertain else [0.91] + [0.01] * 9
        return tuple(prediction_from_probabilities(values, self.manifest, 0.48) for _ in images)


@pytest.mark.parametrize(
    "mode,uncertain,state",
    [
        ("empty", False, "no_detection"),
        ("tiny", False, "detection_unclassified"),
        ("normal", True, "species_uncertain"),
        ("normal", False, "species_recognized"),
    ],
)
def test_states_scores_and_diagnostics(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
    mode: str,
    uncertain: bool,
    state: str,
) -> None:
    video = make_video()
    report = analyze_video(
        video,
        DetectorCase(mode),
        ClassifierCase(classes, uncertain),
        IoUTracker(classes, TrackingConfig()),
        classes,
        LocalStorage(tmp_path / "result"),
        VisionSettings(infer_every_n_frames=2),
    )
    assert report["status"] == state
    assert report["diagnostics"]["frames_analyzed"] == 10
    assert report["diagnostics"]["gpu_elapsed_seconds"] is None
    if mode == "empty":
        assert report["tracks"] == [] and report["diagnostics"]["predictions"] == 0
        assert all(f["state"] == "no_detection" for f in report["frames"])
    else:
        item = report["frames"][0]["detections"][0]
        assert item["box"]["w"] > 0 and item["detection_score"] == 0.83
        assert item["state"] == state
        if mode == "tiny":
            assert item["classification"] is None
            assert item["unclassified_reason"] == "crop_too_small"
        else:
            assert item["classification"]["score"] == (0.1 if uncertain else 0.91)
            assert len(item["classification"]["probabilities"]) == 10
    assert (tmp_path / "result/statistics.json").is_file()


def test_track_threshold_independent_and_uncertain_votes_aggregate(classes: ClassManifest):
    tracker = IoUTracker(classes, TrackingConfig(confidence_threshold=0.7, min_hits=2))
    probabilities = [0.6] + [0.4 / 9] * 9
    observation = Observation(
        detection=Detection(box=Box(x=0, y=0, w=1, h=1), confidence=0.9),
        prediction=prediction_from_probabilities(probabilities, classes, 0.8),
    )
    tracker.update([observation], 0)
    tracker.update([observation], 1)
    assert tracker.summaries()[0]["confidence"] == pytest.approx(0.6)
    assert tracker.summaries()[0]["label"] is None
    assert tracker.metrics()["associations"] == 1
    other = IoUTracker(classes, TrackingConfig(confidence_threshold=0.5, min_hits=2))
    other.update([observation], 0)
    other.update([observation], 1)
    assert other.summaries()[0]["label"] == "chevreuil"


def test_explicit_detection_only_keeps_localized_tracks(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
):
    report = analyze_video(
        make_video(),
        DetectorCase("normal"),
        None,
        IoUTracker(classes, TrackingConfig()),
        classes,
        LocalStorage(tmp_path),
        VisionSettings(detection_only=True, infer_every_n_frames=2),
    )
    assert report["status"] == "detection_unclassified"
    assert report["diagnostics"]["valid_crops"] == 10
    assert report["diagnostics"]["predictions"] == 0
