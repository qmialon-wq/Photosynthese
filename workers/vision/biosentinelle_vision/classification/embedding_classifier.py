"""Classification réelle à partir d'un extracteur local et d'un modèle sklearn local."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL.Image import Image

from ..classes import ClassManifest
from ..datasets.inventory import file_hash
from ..errors import ModelError
from ..schemas import Prediction
from ..storage import LocalStorage
from .adapters import ExistingClassifierAdapter
from .contracts import ClassifierFamily, ClassifierMetadata, ModelVersion
from .embeddings import TimmExtractor
from .model import prediction_from_probabilities


class EmbeddingBackend:
    def __init__(
        self,
        model: Any,
        extractor: TimmExtractor,
        classes: ClassManifest,
        threshold: float,
        batch_size: int,
    ) -> None:
        self.model, self.extractor, self.classes = model, extractor, classes
        self.threshold, self.batch_size = threshold, batch_size

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]:
        import numpy as np

        predictions = []
        for start in range(0, len(images), self.batch_size):
            features = self.extractor.extract(images[start : start + self.batch_size])
            raw = self.model.predict_proba(features)
            full = np.zeros((len(features), len(self.classes.names)))
            full[:, self.model.classes_.astype(int)] = raw
            for row in full:
                predictions.append(
                    prediction_from_probabilities(row.tolist(), self.classes, self.threshold)
                )
        return tuple(predictions)


class EmbeddingClassifier(ExistingClassifierAdapter):
    family: ClassifierFamily = "embedding"

    def load(self, model_version: ModelVersion) -> None:
        import joblib

        if model_version.classifier_family != self.family:
            raise ModelError("Famille incompatible")
        if model_version.sha256 and file_hash(model_version.checkpoint) != model_version.sha256:
            raise ModelError("Manifeste du classificateur corrompu")
        data = json.loads(model_version.checkpoint.read_text(encoding="utf-8"))
        if data.get("schema_version") != "embedding-classifier-1" or data[
            "classes"
        ] != self.manifest.model_dump(mode="json"):
            raise ModelError("Classificateur embeddings incompatible")
        model_path = LocalStorage(model_version.checkpoint.parent).path(data["model_key"])
        if file_hash(model_path) != data["model_sha256"]:
            raise ModelError("Classificateur classique corrompu")
        self.unload()
        # Artefacts joblib exclusivement locaux, produits par l'entraînement de cette application.
        model = joblib.load(model_path)
        profile = data["extractor"]["profile"]
        extractor = TimmExtractor(
            Path(data["pretrained_manifest"]), image_size=profile["image_size"], device=self.device
        )
        if extractor.identity != data["extractor"]:
            raise ModelError("Extracteur différent de celui utilisé à l'entraînement")
        self._classifier = EmbeddingBackend(
            model, extractor, self.manifest, self.threshold, self.batch_size
        )
        self._metadata = ClassifierMetadata(
            model=model_version,
            architecture=data["extractor"]["architecture"],
            class_names=self.manifest.names,
            class_manifest_version=self.manifest.version,
            device=self.device,
            image_size=profile["image_size"],
            label_policy="filename_provisional" if data["weak_validation"] else "human_only",
        )
