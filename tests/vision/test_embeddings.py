import json
from pathlib import Path

import numpy as np
import pytest
from biosentinelle_vision.classification.embeddings import extract_cached
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.training.embedding import train_embedding_classifier

from .test_training_resume import synthetic_training


class TestOnlyExtractor:
    __test__ = False
    identity = {"version": "test-only"}

    def __init__(self):
        self.calls = 0

    def extract(self, images):
        self.calls += 1
        return np.asarray(
            [np.asarray(image).mean(axis=(0, 1)) for image in images], dtype=np.float32
        )


def test_embedding_cache_reuses_content_and_invalidates_model(tmp_path, classes):
    from biosentinelle_vision.schemas import CropsManifest

    settings, records = synthetic_training(tmp_path, classes)
    source = CropsManifest(class_manifest_version=classes.version, crops=records)
    extractor = TestOnlyExtractor()
    cache = LocalStorage(tmp_path / "cache")
    first = extract_cached(source, LocalStorage(settings.output_root), cache, extractor, classes)
    calls = extractor.calls
    second = extract_cached(source, LocalStorage(settings.output_root), cache, extractor, classes)
    assert second["cache_hits"] == 30 and extractor.calls == calls
    extractor.identity = {"version": "test-only-changed"}
    third = extract_cached(source, LocalStorage(settings.output_root), cache, extractor, classes)
    assert third["extracted"] == 30 and third["version"] != first["version"]


@pytest.mark.ml
def test_classical_selection_never_trains_on_validation_or_test(tmp_path, classes):
    pytest.importorskip("sklearn")
    from biosentinelle_vision.schemas import CropsManifest

    settings, records = synthetic_training(tmp_path, classes)
    from biosentinelle_vision.datasets.inventory import file_hash
    from PIL import Image

    for i, record in enumerate(records):
        path = settings.output_root / record.image_key
        with Image.open(path) as original:
            image = original.copy()
        image.putpixel((0, 0), (i, 0, 0))
        image.save(path)
    weights = tmp_path / "test-weights"
    weights.write_bytes(b"test fixture only")
    checksum = file_hash(weights)
    asset = tmp_path / "weights.json"
    asset.write_text(
        json.dumps(
            {
                "schema_version": "pretrained-1",
                "weights_key": weights.name,
                "sha256": checksum,
                "timm_model": "tf_efficientnetv2_b0.in1k",
            }
        )
    )
    extractor = TestOnlyExtractor()
    extractor.identity = {"version": "test-only", "weights_sha256": checksum}
    cache = LocalStorage(tmp_path / "cache")
    index = extract_cached(
        CropsManifest(class_manifest_version=classes.version, crops=records),
        LocalStorage(settings.output_root),
        cache,
        extractor,
        classes,
    )
    result = train_embedding_classifier(
        Path(index["index"]),
        tmp_path / "model",
        tmp_path / "weights.json",
        candidates=("knn", "logistic", "linear_svm"),
    )
    metadata = json.loads((tmp_path / "model/model.json").read_text())
    assert metadata["selection"]["metrics"]["count"] == 10
    assert metadata["skipped"][0]["algorithm"] == "linear_svm"
    assert metadata["weak_validation"] is False
    assert result["checkpoint"].endswith("model.json")
