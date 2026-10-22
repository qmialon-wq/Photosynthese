from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL.Image import Image

from ..classes import ClassManifest
from ..datasets.inventory import file_hash
from ..errors import ModelError
from ..schemas import Prediction
from .preprocessing import build_transform


def create_model(model_name: str, classes: ClassManifest) -> Any:
    import timm

    return timm.create_model(model_name, pretrained=False, num_classes=len(classes.names))


def prediction_from_probabilities(
    probabilities: Sequence[float],
    classes: ClassManifest,
    threshold: float,
) -> Prediction:
    if len(probabilities) != len(classes.names):
        raise ModelError("Nombre de probabilités incompatible avec les classes")
    index = max(range(len(probabilities)), key=probabilities.__getitem__)
    return Prediction(
        probabilities=tuple(probabilities),
        label=classes.names[index] if probabilities[index] >= threshold else None,
    )


class TorchClassifier:
    def __init__(
        self,
        checkpoint: Path,
        classes: ClassManifest,
        *,
        device: str = "cpu",
        threshold: float = 0.48,
        batch_size: int = 4,
    ) -> None:
        if not checkpoint.is_file():
            raise ModelError(f"Checkpoint local absent : {checkpoint}")
        if batch_size < 1 or not 0 <= threshold <= 1 or device not in ("cpu", "cuda"):
            raise ModelError("Configuration du classificateur invalide")
        try:
            import torch

            if device == "cuda" and not torch.cuda.is_available():
                raise ModelError("CUDA demandé mais indisponible")
            data = torch.load(checkpoint, map_location="cpu", weights_only=True)
            self.metadata = {
                "sha256": file_hash(checkpoint),
                "model_name": data["model_name"],
                "image_size": data["img_size"],
                "label_provenance": data.get("label_provenance", {"status": "unknown"}),
            }
            classes.check_checkpoint(data)
            self.model = create_model(data["model_name"], classes)
            self.model.load_state_dict(data["state_dict"], strict=True)
            self.model.to(device).eval()
            self.transform = build_transform(int(data["img_size"]))
        except Exception as exc:
            raise ModelError(f"Chargement classificateur impossible : {exc}") from exc
        self.manifest, self.device = classes, device
        self.threshold, self.batch_size = threshold, batch_size

    @property
    def classes(self) -> tuple[str, ...]:
        return self.manifest.names

    def predict(self, images: Sequence[Image]) -> tuple[Prediction, ...]:
        import torch

        predictions = []
        with torch.inference_mode():
            for start in range(0, len(images), self.batch_size):
                batch = torch.stack(
                    [
                        self.transform(image.convert("RGB"))
                        for image in images[start : start + self.batch_size]
                    ]
                ).to(self.device)
                probabilities = self.model(batch).softmax(-1).cpu().tolist()
                predictions.extend(
                    prediction_from_probabilities(p, self.manifest, self.threshold)
                    for p in probabilities
                )
        return tuple(predictions)
