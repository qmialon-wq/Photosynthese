"""Contrats indépendants de PyTorch et scikit-learn ; aucun chargement implicite."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from ..schemas import Probability, Record

ClassifierFamily = Literal["existing", "supervised", "embedding"]


class ModelVersion(Record):
    model_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    classifier_family: ClassifierFamily
    checkpoint: Path
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    preprocessing_version: str = "legacy-imagenet-resize-v1"


class ClassifierMetadata(Record):
    model: ModelVersion
    architecture: str
    class_names: tuple[str, ...]
    class_manifest_version: str
    device: Literal["cpu", "cuda"]
    image_size: int = Field(ge=1)
    label_policy: str = "unknown"
    timing_method: str = "batch_wall_time_amortized"


class SpeciesPrediction(Record):
    class_id: int | None = Field(default=None, ge=0)
    species_slug: str | None = None
    confidence: Probability | None = None
    scores: dict[str, Probability] = Field(default_factory=dict)
    model_id: str
    model_version: str
    classifier_family: ClassifierFamily
    inference_time_ms: float = Field(ge=0, allow_inf_nan=False)
    status: Literal["recognized", "uncertain", "error"]
    error: str | None = None

    @model_validator(mode="after")
    def coherent(self) -> "SpeciesPrediction":
        if self.status == "error":
            if not self.error or self.scores or self.class_id is not None or self.species_slug:
                raise ValueError("Une erreur ne peut annoncer une classification")
            if self.confidence is not None:
                raise ValueError("Confiance absente pour une erreur")
            return self
        if self.error or not self.scores or abs(sum(self.scores.values()) - 1) > 1e-4:
            raise ValueError("Distribution de classification invalide")
        if self.confidence is None or abs(self.confidence - max(self.scores.values())) > 1e-6:
            raise ValueError("Confiance incompatible avec les scores")
        if self.status == "recognized":
            if self.class_id is None or self.species_slug not in self.scores:
                raise ValueError("Une espèce reconnue exige un indice et un slug")
            if tuple(self.scores)[self.class_id : self.class_id + 1] != (self.species_slug,):
                raise ValueError("Indice incompatible avec le mapping des scores")
            if self.scores[self.species_slug] != self.confidence:
                raise ValueError("L'espèce reconnue doit avoir le meilleur score")
        elif self.class_id is not None or self.species_slug is not None:
            raise ValueError("Une prédiction incertaine ne confirme aucune espèce")
        return self
