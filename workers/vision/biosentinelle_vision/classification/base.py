from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from PIL.Image import Image

from ..schemas import Prediction
from .contracts import ClassifierMetadata, ModelVersion, SpeciesPrediction


class Classifier(Protocol):
    @property
    def classes(self) -> tuple[str, ...]: ...

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]: ...


@runtime_checkable
class SpeciesClassifier(Protocol):
    def load(self, model_version: ModelVersion) -> None: ...

    def predict(self, crop: Image) -> SpeciesPrediction: ...

    def predict_batch(self, crops: Sequence[Image]) -> tuple[SpeciesPrediction, ...]: ...

    def predict_proba(self, crops: Sequence[Image]) -> tuple[tuple[float, ...], ...]: ...

    def get_class_names(self) -> tuple[str, ...]: ...

    def get_metadata(self) -> ClassifierMetadata: ...

    def unload(self) -> None: ...
