from biosentinelle_vision.classification.contracts import ModelVersion, SpeciesPrediction
from biosentinelle_vision.evaluation import comparison

from .test_make_commands import reviewed_dataset


def test_abstentions_are_counted_as_false_negatives(classes):
    metrics = comparison.metrics_with_abstentions(
        ["chevreuil", "chevreuil"], ["chevreuil", None], classes
    )
    assert metrics["accuracy"] == 0.5
    assert metrics["per_class"]["chevreuil"]["recall"] == 0.5
    assert metrics["abstentions"] == {"chevreuil": 1}


def test_comparison_uses_identical_crops_and_reports_failures(tmp_path, classes, monkeypatch):
    settings, _ = reviewed_dataset(tmp_path, classes)
    checkpoint = tmp_path / "test-only.pt"
    checkpoint.write_bytes(b"test-only")

    class TestClassifier:
        def predict_batch(self, images):
            return tuple(
                SpeciesPrediction(
                    class_id=0,
                    species_slug="chevreuil",
                    confidence=1,
                    scores=dict(zip(classes.names, [1.0] + [0.0] * 9, strict=False)),
                    model_id="test",
                    model_version="1",
                    classifier_family="existing",
                    inference_time_ms=0,
                    status="recognized",
                )
                for _ in images
            )

        def unload(self):
            pass

    monkeypatch.setattr(comparison, "load_classifier", lambda *a, **k: TestClassifier())
    result = comparison.compare_classifiers(
        tmp_path / "review.json",
        settings.output_root,
        [
            ModelVersion(
                model_id="test", version="1", classifier_family="existing", checkpoint=checkpoint
            )
        ],
        tmp_path / "report.json",
        classes,
        lock=tmp_path / "lock",
    )
    assert result["human_validated"] and result["protocol"]["split"] == "val"
    assert result["models"][0]["metrics"]["count"] == 10
    assert result["models"][0]["coverage"] == 1
    assert result["models"][0]["videos"]["accuracy"] is None
