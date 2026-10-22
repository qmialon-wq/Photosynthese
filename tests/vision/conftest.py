from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import pytest
from biosentinelle_vision.classes import ClassManifest, load_classes


@pytest.fixture
def classes() -> ClassManifest:
    return load_classes()


@pytest.fixture
def make_video(tmp_path: Path) -> Callable[..., Path]:
    def create(name: str = "Renards-Scene-001.avi", frames: int = 20, shade: int = 40) -> Path:
        path = tmp_path / "dataset" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
        assert writer.isOpened(), "Codec MJPG requis pour les fixtures synthétiques"
        try:
            for index in range(frames):
                image = np.full((48, 64, 3), shade + index, dtype=np.uint8)
                cv2.rectangle(image, (index, 8), (index + 10, 30), (10, 180, 30), -1)
                writer.write(image)
        finally:
            writer.release()
        return path

    return create
