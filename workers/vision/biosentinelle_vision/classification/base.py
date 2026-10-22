from collections.abc import Sequence
from typing import Protocol

from PIL.Image import Image

from ..schemas import Prediction


class Classifier(Protocol):
    @property
    def classes(self) -> tuple[str, ...]: ...

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]: ...
