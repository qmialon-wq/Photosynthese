"""Contrats de soumission sans dépendances ML ; calculs réservés au worker."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.vision_jobs import AnalysisRequest

Architecture = Literal["tf_efficientnetv2_b0", "efficientnetv2_s", "convnext_tiny", "resnet50"]


class OperationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Extract(OperationBody):
    manifest_key: str
    storage_key: str = ""
    architecture: Architecture = "tf_efficientnetv2_b0"
    image_size: int = Field(default=224, ge=32, le=512)
    batch_size: int = Field(default=2, ge=1, le=32)
    allow_weak_labels: bool = False

    @field_validator("manifest_key", "storage_key")
    @classmethod
    def relative(cls, value: str) -> str:
        return AnalysisRequest(video=value or ".").video if value else ""


class EmbeddingTraining(OperationBody):
    index_key: str
    architecture: Architecture = "tf_efficientnetv2_b0"
    candidates: list[Literal["logistic", "knn", "linear_svm", "rbf_svm"]] = Field(
        default=["logistic", "knn", "linear_svm"], min_length=1, max_length=4
    )
    allow_weak_validation: bool = False
    seed: int = 42

    _relative = field_validator("index_key")(Extract.relative.__func__)


class Clustering(OperationBody):
    index_key: str
    clusters: int = Field(default=10, ge=2, le=100)
    method: Literal["kmeans", "hdbscan"] = "kmeans"
    seed: int = 42

    _relative = field_validator("index_key")(Extract.relative.__func__)


class DatasetPreparation(OperationBody):
    allow_weak_labels: bool = False
    exclude_blurry: bool = True


class Comparison(OperationBody):
    manifest_key: str
    storage_key: str = ""
    model_ids: list[UUID] = Field(min_length=1, max_length=8)
    split: Literal["val", "test"] = "val"
    confirm_final_test: bool = False
    threshold: float = Field(default=0.48, ge=0, le=1)
    batch_size: int = Field(default=2, ge=1, le=32)
    video_truth_key: str | None = None
    allow_weak_labels: bool = False

    _relative = field_validator("manifest_key", "storage_key")(Extract.relative.__func__)

    @field_validator("video_truth_key")
    @classmethod
    def truth_relative(cls, value: str | None) -> str | None:
        return Extract.relative(value) if value else None


class Promotion(OperationBody):
    comparison_id: UUID
    manual_reason: str = Field(default="", max_length=2000)


class Rollback(OperationBody):
    reason: str = Field(min_length=3, max_length=2000)
