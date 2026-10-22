from pathlib import Path
from unittest.mock import MagicMock

import pytest
from biosentinelle_vision.classification.adapters import (
    ExistingClassifierAdapter,
    LegacyClassifierBridge,
    SupervisedClassifier,
)
from biosentinelle_vision.classification.base import SpeciesClassifier
from biosentinelle_vision.classification.contracts import ModelVersion, SpeciesPrediction
from biosentinelle_vision.errors import ModelError
from biosentinelle_vision.schemas import Prediction
from PIL import Image


@pytest.mark.parametrize(
    "adapter_type,family",
    [(ExistingClassifierAdapter, "existing"), (SupervisedClassifier, "supervised")],
)
def test_adapter_preserves_legacy_predictions_and_lifecycle(
    tmp_path, classes, monkeypatch, adapter_type, family
):
    from biosentinelle_vision.classification import model

    checkpoint = tmp_path / "fixture.pt"
    checkpoint.write_bytes(b"test-only-not-a-model")
    raw = Prediction(probabilities=(0.9, 0.1, *([0.0] * 8)), label="chevreuil")
    classifier = MagicMock()
    classifier.metadata = {"model_name": "fixture", "image_size": 224}
    classifier.predict.return_value = (raw,)
    loader = MagicMock(return_value=classifier)
    monkeypatch.setattr(model, "TorchClassifier", loader)
    adapter = adapter_type(classes)
    assert isinstance(adapter, SpeciesClassifier)
    loader.assert_not_called()
    with pytest.raises(ModelError, match="explicitement"):
        adapter.predict(Image.new("RGB", (32, 32)))
    adapter.load(
        ModelVersion(
            model_id="fixture", version="v1", classifier_family=family, checkpoint=checkpoint
        )
    )
    result = adapter.predict(Image.new("RGB", (32, 32)))
    assert result.class_id == 0 and result.species_slug == "chevreuil"
    assert result.confidence == 0.9 and result.classifier_family == family
    assert result.status == "recognized" and result.inference_time_ms >= 0
    assert tuple(result.scores) == classes.names
    assert adapter.predict_proba([Image.new("RGB", (32, 32))]) == (raw.probabilities,)
    assert LegacyClassifierBridge(adapter).predict([Image.new("RGB", (32, 32))]) == (raw,)
    assert adapter.predict_batch([]) == ()
    classifier.predict.side_effect = RuntimeError("test failure")
    assert adapter.predict(Image.new("RGB", (32, 32))).status == "error"
    with pytest.raises(ModelError):
        LegacyClassifierBridge(adapter).predict([Image.new("RGB", (32, 32))])
    adapter.unload()
    adapter.unload()
    with pytest.raises(ModelError):
        adapter.get_metadata()


def test_adapter_rejects_missing_weights_and_bad_integrity(tmp_path, classes):
    adapter = ExistingClassifierAdapter(classes)
    version = ModelVersion(
        model_id="test",
        version="v1",
        classifier_family="existing",
        checkpoint=tmp_path / "missing.pt",
    )
    with pytest.raises(ModelError, match="absent"):
        adapter.load(version)
    version.checkpoint.write_bytes(b"test-only")
    with pytest.raises(ModelError, match="Empreinte"):
        adapter.load(version.model_copy(update={"sha256": "0" * 64}))


def test_prediction_rejects_fabricated_or_inconsistent_success():
    fields = dict(
        model_id="a", model_version="v1", classifier_family="existing", inference_time_ms=1
    )
    with pytest.raises(ValueError):
        SpeciesPrediction(
            **fields,
            status="recognized",
            scores={"chevreuil": 1},
            confidence=1,
            class_id=0,
            species_slug="merle",
        )
    with pytest.raises(ValueError):
        SpeciesPrediction(**fields, status="error", error="bad", confidence=0.9)


@pytest.mark.ml
def test_real_adapter_cpu_checkpoint(tmp_path: Path, classes):
    torch = pytest.importorskip("torch")
    pytest.importorskip("timm")
    from biosentinelle_vision.classification.model import create_model

    torch.set_num_threads(2)
    checkpoint = tmp_path / "test.pt"
    torch.save(
        {
            "model_name": "mobilenetv3_small_050",
            "img_size": 32,
            "classes": list(classes.names),
            "class_manifest_version": classes.version,
            "state_dict": create_model("mobilenetv3_small_050", classes).state_dict(),
        },
        checkpoint,
    )
    adapter = SupervisedClassifier(classes)
    adapter.load(
        ModelVersion(
            model_id="test-only", version="1", classifier_family="supervised", checkpoint=checkpoint
        )
    )
    result = adapter.predict(Image.new("RGB", (32, 32)))
    assert result.status in ("recognized", "uncertain")
    assert len(result.scores) == 10
    adapter.unload()
