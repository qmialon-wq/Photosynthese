from typing import Protocol

from PIL.Image import Image

from ..schemas import Detection


class Detector(Protocol):
    @property
    def identity(self) -> str: ...

    def detect(self, image: Image) -> tuple[Detection, ...]: ...
