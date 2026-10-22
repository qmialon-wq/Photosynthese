import inspect
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from PIL.Image import Image

from ..config import VisionSettings
from ..errors import ModelError
from ..schemas import Box, Detection
from .weights import MODEL_ID, PACKAGE_VERSION, verify_weights


def api_diagnostics() -> dict[str, str]:
    try:
        installed = version("megadetector")
        if installed != PACKAGE_VERSION:
            raise ModelError(
                f"MegaDetector {installed} installé ; version testée requise : {PACKAGE_VERSION}"
            )
        from megadetector.detection import pytorch_detector, run_detector

        loader = inspect.signature(run_detector.load_detector)
        inference = inspect.signature(pytorch_detector.PTDetector.generate_detections_one_image)
        loader.bind("local.pt", force_cpu=True, force_model_download=False)
        inference.bind(None, None, detection_threshold=0.1)
        return {
            "package_version": installed,
            "load_detector": str(loader),
            "generate_detections_one_image": str(inference),
            "model_id": MODEL_ID,
        }
    except (ImportError, PackageNotFoundError, TypeError, AttributeError) as exc:
        raise ModelError(
            f"API MegaDetector incompatible ou absente : {exc}. Construire l'image ML."
        ) from exc


class MegaDetector:
    """Adaptateur réel. Construction explicite avec un fichier de poids local."""

    def __init__(self, weights: Path, settings: VisionSettings) -> None:
        weights = weights.resolve()
        digest = verify_weights(weights)
        self.diagnostics = api_diagnostics()
        self.threshold = settings.detection_threshold
        self._identity = (
            f"megadetector:{MODEL_ID}:{PACKAGE_VERSION}:{digest}:threshold={self.threshold}"
        )
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
                f"Chargement MegaDetector {PACKAGE_VERSION}/{MODEL_ID} impossible ({weights}, "
                f"device={settings.device}) : {type(exc).__name__}: {exc}"
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
