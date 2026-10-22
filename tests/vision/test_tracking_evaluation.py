from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.classification.model import prediction_from_probabilities
from biosentinelle_vision.cli import main
from biosentinelle_vision.config import TrackingConfig
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.evaluation.metrics import evaluate_predictions
from biosentinelle_vision.schemas import Box, Detection, LabeledPrediction, PredictionsManifest
from biosentinelle_vision.tracking.base import Observation
from biosentinelle_vision.tracking.iou import IoUTracker, iou


def probabilities(index: int = 0) -> tuple[float, ...]:
    return tuple(1.0 if i == index else 0.0 for i in range(10))


def test_tracking_one_to_one_expiration_and_uncertainty(classes: ClassManifest) -> None:
    box = Box(x=0.1, y=0.1, w=0.4, h=0.4)
    assert iou(box, box) == pytest.approx(1)
    tracker = IoUTracker(classes, TrackingConfig(max_misses=0, min_hits=2))
    obs = Observation(
        detection=Detection(box=box, confidence=0.8),
        prediction=prediction_from_probabilities(probabilities(), classes, 0.48),
    )
    first = tracker.update([obs], 0)
    second = tracker.update([obs, obs], 1)
    assert first[0].track_id in {item.track_id for item in second}
    assert len({item.track_id for item in second}) == 2
    assert tracker.summaries()[0]["label"] == "chevreuil"
    tracker.update([], 2)
    assert tracker.update([obs], 3)[0].track_id not in {item.track_id for item in second}
    with pytest.raises(ValueError, match="croissants"):
        tracker.update([], 3)
    uncertain = prediction_from_probabilities([0.1] * 10, classes, 0.48)
    assert uncertain.label is None


def prediction_manifest(classes: ClassManifest) -> PredictionsManifest:
    return PredictionsManifest(
        class_manifest_version=classes.version,
        classes=classes.names,
        predictions=(
            LabeledPrediction(
                crop_id="a",
                video_id="v",
                truth="chevreuil",
                human_validated=True,
                probabilities=probabilities(),
            ),
        ),
    )


def test_evaluation_requires_human_truth_and_does_not_invent_video_truth(
    classes: ClassManifest,
    tmp_path: Path,
) -> None:
    source = prediction_manifest(classes)
    result = evaluate_predictions(source, classes)
    assert result["crops"]["accuracy"] == 1
    assert result["crops"]["macro_f1"] == pytest.approx(0.1)
    assert len(result["crops"]["confusion_matrix"]) == 10
    assert result["videos"]["count"] == 0
    assert result["videos_without_human_truth"] == ["v"]
    source = source.model_copy(update={"video_truth": {"v": "chevreuil"}})
    assert evaluate_predictions(source, classes)["videos"]["accuracy"] == 1
    weak = source.predictions[0].model_copy(update={"human_validated": False})
    with pytest.raises(ManifestError, match="humainement"):
        evaluate_predictions(source.model_copy(update={"predictions": (weak,)}), classes)
    path, output = tmp_path / "predictions.json", tmp_path / "metrics.json"
    path.write_text(source.model_dump_json(), encoding="utf-8")
    assert main(["evaluate", "--predictions", str(path), "--output", str(output)]) == 0
    assert output.is_file()
