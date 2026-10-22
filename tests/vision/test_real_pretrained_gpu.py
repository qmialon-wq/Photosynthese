"""Test facultatif de mécanique GPU ; aucune mesure de qualité écologique."""

import os
from pathlib import Path

import pytest

from .test_training_resume import synthetic_training

pytestmark = [pytest.mark.gpu, pytest.mark.real_model]


def test_real_local_imagenet_training_and_checkpoint(tmp_path, classes):
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA requis")
    asset = Path(
        os.getenv(
            "BIOSENTINELLE_PRETRAINED_TEST_MANIFEST",
            "/storage/models/pretrained/tf_efficientnetv2_b0/manifest.json",
        )
    )
    if not asset.is_file():
        pytest.skip("Préparer les vrais poids explicitement avec pretrained-fetch")
    from biosentinelle_vision.classification.contracts import ModelVersion
    from biosentinelle_vision.classification.factory import load_classifier
    from biosentinelle_vision.storage import LocalStorage
    from biosentinelle_vision.training.engine import train
    from PIL import Image

    torch.set_num_threads(2)
    settings, records = synthetic_training(tmp_path, classes)
    settings.device = "cuda"
    settings.gpu_lock_path = tmp_path / "gpu.lock"
    settings.training.initialization = "pretrained"
    settings.training.pretrained_manifest = asset
    settings.training.model_name = "tf_efficientnetv2_b0"
    settings.training.image_size = 224
    settings.training.epochs_head = settings.training.epochs_finetune = 1
    result = train(records, LocalStorage(settings.output_root), classes, settings)
    assert len(result["history"]) == 2
    version = ModelVersion(
        model_id="test-only",
        version="gpu-test",
        classifier_family="supervised",
        checkpoint=Path(result["checkpoint"]),
        preprocessing_version="timm-local-imagenet-v1",
    )
    classifier = load_classifier(version, classes, device="cuda", batch_size=2)
    try:
        predicted = classifier.predict(Image.new("RGB", (224, 224), "gray"))
        assert predicted.status != "error" and len(predicted.scores) == 10
    finally:
        classifier.unload()


def test_real_embeddings_and_classical_model_roundtrip(tmp_path, classes):
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA requis")
    asset = Path(
        os.getenv(
            "BIOSENTINELLE_PRETRAINED_TEST_MANIFEST",
            "/storage/models/pretrained/tf_efficientnetv2_b0/manifest.json",
        )
    )
    if not asset.is_file():
        pytest.skip("Poids généralistes locaux requis")
    from biosentinelle_vision.classification.contracts import ModelVersion
    from biosentinelle_vision.classification.embeddings import extract_embeddings
    from biosentinelle_vision.classification.factory import load_classifier
    from biosentinelle_vision.training.embedding import train_embedding_classifier
    from PIL import Image
    from threadpoolctl import threadpool_limits

    torch.set_num_threads(2)
    settings, records = synthetic_training(tmp_path, classes)
    # Contenu distinct entre les splits, sans prétendre représenter un vrai animal.
    for i, record in enumerate(records):
        path = settings.output_root / record.image_key
        with Image.open(path) as original:
            image = original.copy()
        image.putpixel((0, 0), (i, 0, 0))
        image.save(path)
    index = extract_embeddings(
        settings.train_manifest,
        settings.output_root,
        tmp_path / "embeddings",
        asset,
        device="cuda",
        batch_size=2,
        lock=tmp_path / "gpu.lock",
    )
    with threadpool_limits(limits=2):
        result = train_embedding_classifier(
            Path(index["index"]),
            tmp_path / "model",
            asset,
            candidates=("logistic",),
        )
    version = ModelVersion(
        model_id="test-embedding",
        version="test",
        classifier_family="embedding",
        checkpoint=Path(result["checkpoint"]),
        preprocessing_version="timm-local-imagenet-v1",
    )
    classifier = load_classifier(version, classes, device="cuda", batch_size=2)
    try:
        prediction = classifier.predict(Image.new("RGB", (224, 224), "gray"))
        assert prediction.status != "error" and len(prediction.scores) == 10
    finally:
        classifier.unload()
