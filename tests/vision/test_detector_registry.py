import hashlib
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from biosentinelle_vision.detection import megadetector, weights
from biosentinelle_vision.errors import ModelError


def test_weight_cache_integrity_and_failed_download_is_atomic(tmp_path: Path, monkeypatch):
    content = b"test-only-weight-fixture-not-an-ML-model"
    monkeypatch.setattr(weights, "MODEL_SHA256", hashlib.sha256(content).hexdigest())
    monkeypatch.setattr(weights, "MODEL_MD5", hashlib.md5(content).hexdigest())
    calls = []

    def download(*args, **kwargs):
        calls.append(True)
        return BytesIO(content)

    monkeypatch.setattr(weights, "urlopen", download)
    target = tmp_path / "model.pt"
    assert not weights.fetch_weights(target)["cached"]
    assert weights.fetch_weights(target)["cached"]
    assert len(calls) == 1 and (tmp_path / "model.pt.manifest.json").is_file()
    target.write_bytes(b"corrupt")
    with pytest.raises(ModelError, match="corrompus"):
        weights.fetch_weights(target)
    assert len(calls) == 1
    target.unlink()
    monkeypatch.setattr(weights, "urlopen", lambda *a, **k: BytesIO(b"invalid"))
    with pytest.raises(ModelError, match="corrompus"):
        weights.fetch_weights(target)
    assert not target.exists() and not list(tmp_path.glob(".model.pt-*"))


def test_api_signatures_and_version_are_checked(monkeypatch):
    monkeypatch.setattr(megadetector, "version", lambda _: "wrong-version")
    with pytest.raises(ModelError, match="version testée"):
        megadetector.api_diagnostics()
    monkeypatch.setattr(megadetector, "version", lambda _: weights.PACKAGE_VERSION)
    parent = ModuleType("megadetector")
    detection = ModuleType("megadetector.detection")
    detection.run_detector = SimpleNamespace(load_detector=lambda model_file: None)
    detection.pytorch_detector = SimpleNamespace(
        PTDetector=SimpleNamespace(
            generate_detections_one_image=lambda self, image: None,
        )
    )
    monkeypatch.setitem(sys.modules, "megadetector", parent)
    monkeypatch.setitem(sys.modules, "megadetector.detection", detection)
    with pytest.raises(ModelError, match="API MegaDetector incompatible"):
        megadetector.api_diagnostics()
