from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.classification.model import TorchClassifier
from biosentinelle_vision.commands import train_from_manifest
from biosentinelle_vision.config import TrainingConfig, VisionSettings
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.evaluation.metrics import evaluate_predictions
from biosentinelle_vision.evaluation.predict import predict_test_crops
from biosentinelle_vision.schemas import Box, CropRecord, CropsManifest, FrameRecord
from biosentinelle_vision.storage import LocalStorage
from PIL import Image

pytestmark = pytest.mark.ml


@pytest.mark.parametrize("provisional", [False, True])
def test_real_torch_training_checkpoint_and_evaluation_on_cpu(
    tmp_path: Path,
    classes: ClassManifest,
    provisional: bool,
) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("timm")
    torch.set_num_threads(1)
    storage = LocalStorage(tmp_path / "images")
    records = []
    for split in ("train", "val", "test"):
        for i, name in enumerate(classes.names):
            key = f"{split}/{i}.png"
            storage.path(key).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (48, 48), (i * 20, 30, 80)).save(storage.path(key))
            frame = FrameRecord(
                video_id=f"{split}-{i}",
                group_id=f"{split}-{i}",
                frame_index=0,
                time_seconds=0,
                image_key=key,
                split=split,
                species_candidate=name,
            )
            records.append(
                CropRecord(
                    crop_id=f"{split}-{i}",
                    image_key=key,
                    frame=frame,
                    box=Box(x=0, y=0, w=1, h=1),
                    detection_confidence=0.9,
                    review="pending" if provisional else "accept",
                    label=name,
                )
            )
    settings = VisionSettings(
        device="cpu",
        train_manifest=storage.path("review.json"),
        initial_checkpoint=None,
        output_root=storage.root,
        checkpoint_root=tmp_path / "checkpoints",
        training=TrainingConfig(
            initialization="scratch",
            allow_filename_labels=provisional,
            model_name="mobilenetv3_small_050",
            image_size=32,
            batch_size=2,
            epochs_head=1,
            epochs_finetune=1,
        ),
    )
    storage.write_json(
        "review.json",
        CropsManifest(
            class_manifest_version=classes.version,
            crops=tuple(records),
        ).model_dump(mode="json"),
    )
    result = train_from_manifest(settings, classes)
    assert len(result["history"]) == 2
    assert Path(result["checkpoint"]).is_file()
    checkpoint = torch.load(result["checkpoint"], weights_only=True, map_location="cpu")
    assert checkpoint["classes"] == list(classes.names)
    assert checkpoint["class_manifest_version"] == classes.version
    assert checkpoint["label_provenance"]["validation_human_validated"] is (not provisional)
    assert all(
        row["validation"]["human_validated"] is (not provisional) for row in result["history"]
    )
    classifier = TorchClassifier(Path(result["checkpoint"]), classes, batch_size=2)
    if provisional:
        with pytest.raises(ManifestError, match="humainement"):
            predict_test_crops(records, classifier, classes, storage)
        return
    predictions = predict_test_crops(records, classifier, classes, storage)
    assert len(predictions.predictions) == 10
    report = evaluate_predictions(predictions, classes)
    assert report["crops"]["count"] == 10
    assert report["videos"]["count"] == 0
