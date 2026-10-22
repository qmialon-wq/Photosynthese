from collections.abc import Mapping, Sequence
from io import BytesIO

from PIL import Image

from ..classes import ClassManifest
from ..classification.base import Classifier
from ..errors import ManifestError, ModelError
from ..schemas import CropRecord, LabeledPrediction, PredictionsManifest
from ..storage.base import Storage
from ..training.dataset import select_samples


def predict_test_crops(
    records: Sequence[CropRecord],
    classifier: Classifier,
    classes: ClassManifest,
    storage: Storage,
    *,
    human_video_truth: Mapping[str, str] | None = None,
    max_per_video: int = 18,
) -> PredictionsManifest:
    if classifier.classes != classes.names:
        raise ModelError("Classes du classificateur incompatibles")
    selected = [
        r for r in select_samples(records, classes, max_per_video) if r.frame.split == "test"
    ]
    if not selected:
        raise ManifestError("Aucun crop test validé humainement")
    predictions = []
    for record in selected:
        with Image.open(BytesIO(storage.read_bytes(record.image_key))) as image:
            result = classifier.predict([image.convert("RGB")])
        if len(result) != 1:
            raise ModelError("Une prédiction par crop est requise")
        predictions.append(
            LabeledPrediction(
                crop_id=record.crop_id,
                video_id=record.frame.video_id,
                truth=record.label,
                human_validated=True,
                probabilities=result[0].probabilities,
            )
        )
    manifest = PredictionsManifest(
        class_manifest_version=classes.version,
        classes=classes.names,
        predictions=tuple(predictions),
        video_truth=dict(human_video_truth or {}),
    )
    storage.write_json("predictions.json", manifest.model_dump(mode="json"))
    return manifest
