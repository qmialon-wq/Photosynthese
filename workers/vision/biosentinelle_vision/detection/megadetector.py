from pathlib import Path
from typing import Any

from PIL.Image import Image

from ..config import VisionSettings
from ..datasets.inventory import file_hash
from ..errors import ModelError
from ..schemas import Box, Detection


class MegaDetector:
    """Adaptateur réel. Construction explicite avec un fichier de poids local."""

    def __init__(self, weights: Path, settings: VisionSettings) -> None:
        weights = weights.resolve()
        if not weights.is_file() or weights.suffix.lower() != ".pt":
            raise ModelError(f"Poids MegaDetector .pt locaux manquants : {weights}")
        self.threshold = settings.detection_threshold
        self._identity = f"megadetector:{file_hash(weights)}:threshold={self.threshold}"
        try:
            from megadetector.detection import run_detector

            if settings.device == "cuda":
                import torch

                if not torch.cuda.is_available():
                    raise ModelError("CUDA demandé mais indisponible")
            self._model: Any = run_detector.load_detector(
                str(weights), force_cpu=settings.device == "cpu", force_model_download=False
            )
        except Exception as exc:
            raise ModelError(
                "Chargement MegaDetector impossible ; installer l'extra ml, vérifier les poids "
                "locaux et les versions. Aucun détecteur de remplacement."
            ) from exc

    @property
    def identity(self) -> str:
        return self._identity

    def detect(self, image: Image) -> tuple[Detection, ...]:
        try:
            result = self._model.generate_detections_one_image(
                image.convert("RGB"), detection_threshold=self.threshold
            )
            if result.get("failure"):
                raise ModelError(str(result["failure"]))
            if "detections" not in result:
                raise ModelError("Réponse MegaDetector sans champ detections")
            return tuple(
                Detection(
                    box=Box(**dict(zip(("x", "y", "w", "h"), item["bbox"], strict=True))),
                    confidence=item["conf"],
                )
                for item in result["detections"]
                if str(item.get("category")) == "1" and item["conf"] >= self.threshold
            )
        except Exception as exc:
            raise ModelError(f"Inférence MegaDetector impossible : {exc}") from exc
