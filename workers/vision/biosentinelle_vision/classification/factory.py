from ..classes import ClassManifest
from .adapters import ExistingClassifierAdapter, SupervisedClassifier
from .base import SpeciesClassifier
from .contracts import ModelVersion


def load_classifier(
    version: ModelVersion,
    classes: ClassManifest,
    *,
    device: str = "cpu",
    threshold: float = 0.48,
    batch_size: int = 2,
) -> SpeciesClassifier:
    if version.classifier_family == "embedding":
        from .embedding_classifier import EmbeddingClassifier

        classifier = EmbeddingClassifier(
            classes, device=device, threshold=threshold, batch_size=batch_size
        )
    else:
        adapter = (
            ExistingClassifierAdapter
            if version.classifier_family == "existing"
            else SupervisedClassifier
        )
        classifier = adapter(classes, device=device, threshold=threshold, batch_size=batch_size)
    classifier.load(version)
    return classifier
