"""Adaptateurs réels des checkpoints locaux, compatibles avec le pipeline historique."""

import gc
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from PIL.Image import Image

from ..classes import ClassManifest
from ..datasets.inventory import file_hash
from ..errors import ModelError
from ..schemas import Prediction
from .base import SpeciesClassifier
from .contracts import ClassifierFamily, ClassifierMetadata, ModelVersion, SpeciesPrediction

if TYPE_CHECKING:
    from .model import TorchClassifier


class ExistingClassifierAdapter:
    family: ClassifierFamily = "existing"

    def __init__(
        self,
        classes: ClassManifest,
        *,
        device: str = "cpu",
        threshold: float = 0.48,
        batch_size: int = 4,
    ) -> None:
        if device not in ("cpu", "cuda") or not 0 <= threshold <= 1 or batch_size < 1:
            raise ModelError("Configuration du classificateur invalide")
        self.manifest, self.device = classes, device
        self.threshold, self.batch_size = threshold, batch_size
        self._classifier: TorchClassifier | None = None
        self._metadata: ClassifierMetadata | None = None

    def load(self, model_version: ModelVersion) -> None:
        from .model import TorchClassifier

        if model_version.classifier_family != self.family:
            raise ModelError("Famille de modèle incompatible avec l'adaptateur")
        if model_version.preprocessing_version not in (
            "legacy-imagenet-resize-v1",
            "timm-local-imagenet-v1",
        ):
            raise ModelError("Prétraitement du checkpoint non pris en charge par cet adaptateur")
        if not model_version.checkpoint.is_file():
            raise ModelError(f"Checkpoint local absent : {model_version.checkpoint}")
        digest = file_hash(model_version.checkpoint)
        if model_version.sha256 and model_version.sha256 != digest:
            raise ModelError("Empreinte du checkpoint incompatible")
        self.unload()
        classifier = TorchClassifier(
            model_version.checkpoint,
            self.manifest,
            device=self.device,
            threshold=self.threshold,
            batch_size=self.batch_size,
        )
        profile_version = (classifier.metadata.get("preprocessing") or {}).get(
            "version", "legacy-imagenet-resize-v1"
        )
        if profile_version != model_version.preprocessing_version:
            raise ModelError("Version du prétraitement incompatible avec le checkpoint")
        metadata = ClassifierMetadata(
            model=model_version.model_copy(update={"sha256": digest}),
            architecture=classifier.metadata["model_name"],
            class_names=self.manifest.names,
            class_manifest_version=self.manifest.version,
            device=self.device,
            image_size=classifier.metadata["image_size"],
            label_policy=classifier.metadata.get("label_provenance", {}).get(
                "label_policy", "unknown"
            ),
        )
        self._classifier, self._metadata = classifier, metadata

    def get_class_names(self) -> tuple[str, ...]:
        return self.manifest.names

    def get_metadata(self) -> ClassifierMetadata:
        if self._metadata is None:
            raise ModelError("Charger explicitement une version avant de prédire")
        return self._metadata

    def predict(self, crop: Image) -> SpeciesPrediction:
        return self.predict_batch([crop])[0]

    def predict_batch(self, crops: Sequence[Image]) -> tuple[SpeciesPrediction, ...]:
        metadata = self.get_metadata()
        if not crops:
            return ()
        began = time.perf_counter()
        try:
            predictions = self._classifier.predict(crops)
            if len(predictions) != len(crops):
                raise ModelError("Une prédiction par recadrage est requise")
            elapsed = (time.perf_counter() - began) * 1000 / len(crops)
            return tuple(
                SpeciesPrediction(
                    class_id=self.manifest.names.index(p.label) if p.label else None,
                    species_slug=p.label,
                    confidence=max(p.probabilities),
                    scores=dict(zip(self.manifest.names, p.probabilities, strict=True)),
                    model_id=metadata.model.model_id,
                    model_version=metadata.model.version,
                    classifier_family=self.family,
                    inference_time_ms=elapsed,
                    status="recognized" if p.label else "uncertain",
                )
                for p in predictions
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - began) * 1000 / len(crops)
            return tuple(
                SpeciesPrediction(
                    model_id=metadata.model.model_id,
                    model_version=metadata.model.version,
                    classifier_family=self.family,
                    inference_time_ms=elapsed,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
                for _ in crops
            )

    def predict_proba(self, crops: Sequence[Image]) -> tuple[tuple[float, ...], ...]:
        results = self.predict_batch(crops)
        if any(result.status == "error" for result in results):
            raise ModelError("Échec de classification : probabilités indisponibles")
        return tuple(
            tuple(result.scores[name] for name in self.manifest.names) for result in results
        )

    def unload(self) -> None:
        loaded = self._classifier is not None
        self._classifier, self._metadata = None, None
        if loaded:
            gc.collect()
            if self.device == "cuda":
                import torch

                torch.cuda.empty_cache()


class SupervisedClassifier(ExistingClassifierAdapter):
    family: ClassifierFamily = "supervised"


class LegacyClassifierBridge:
    """Conversion explicite vers le contrat batché des détecteurs/tracks existants."""

    def __init__(self, classifier: SpeciesClassifier) -> None:
        self.classifier = classifier

    @property
    def classes(self) -> tuple[str, ...]:
        return self.classifier.get_class_names()

    @property
    def metadata(self) -> dict:
        return self.classifier.get_metadata().model_dump(mode="json")

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]:
        results = self.classifier.predict_batch(images)
        if any(result.status == "error" for result in results):
            raise ModelError(next(result.error for result in results if result.status == "error"))
        return tuple(
            Prediction(
                probabilities=tuple(r.scores[name] for name in self.classes), label=r.species_slug
            )
            for r in results
        )
