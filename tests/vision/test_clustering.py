import json
from pathlib import Path

import pytest
from biosentinelle_vision.classification.embeddings import extract_cached
from biosentinelle_vision.evaluation.clustering import cluster_embeddings
from biosentinelle_vision.schemas import CropsManifest
from biosentinelle_vision.storage import LocalStorage

from .test_embeddings import TestOnlyExtractor
from .test_training_resume import synthetic_training


@pytest.mark.parametrize("method", ["kmeans", "hdbscan"])
def test_exploration_fits_train_and_never_labels_species_or_exposes_test(tmp_path, classes, method):
    pytest.importorskip("sklearn")
    settings, records = synthetic_training(tmp_path, classes)
    original = CropsManifest(class_manifest_version=classes.version, crops=records)
    index = extract_cached(
        original,
        LocalStorage(settings.output_root),
        LocalStorage(tmp_path / "cache"),
        TestOnlyExtractor(),
        classes,
    )
    output = tmp_path / "clusters.json"
    result = cluster_embeddings(Path(index["index"]), output, clusters=3, method=method)
    report = json.loads(output.read_text())
    assert result["points"] == 20 and report["test_excluded"]
    assert all(p["split"] != "test" and "predicted_species" not in p for p in report["points"])
    assert report["projection"] == "pca_train_only"
