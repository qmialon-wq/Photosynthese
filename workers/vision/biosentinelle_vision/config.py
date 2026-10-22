from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FramesConfig(BaseModel):
    max_per_video: int = Field(default=24, ge=1)
    min_seconds_between: float = Field(default=0.8, gt=0, allow_inf_nan=False)
    jpeg_quality: int = Field(default=90, ge=1, le=100)


class CropsConfig(BaseModel):
    min_side: int = Field(default=28, ge=1)
    margin: float = Field(default=0.12, ge=0, le=1)
    max_per_frame: int = Field(default=4, ge=1)
    max_per_video: int = Field(default=18, ge=1)


class SplitConfig(BaseModel):
    validation_fraction: float = Field(default=0.15, ge=0, lt=1)
    test_fraction: float = Field(default=0.15, ge=0, lt=1)

    @model_validator(mode="after")
    def validate_fractions(self) -> "SplitConfig":
        if self.validation_fraction + self.test_fraction >= 1:
            raise ValueError("Les fractions doivent laisser un ensemble train")
        return self


class TrackingConfig(BaseModel):
    iou_threshold: float = Field(default=0.18, gt=0, le=1)
    max_misses: int = Field(default=5, ge=0)
    min_hits: int = Field(default=2, ge=1)


class TrainingConfig(BaseModel):
    allow_filename_labels: bool = False
    model_name: str = "convnext_tiny"
    image_size: int = Field(default=256, ge=32)
    batch_size: int = Field(default=4, ge=1)
    num_workers: int = Field(default=0, ge=0)
    epochs_head: int = Field(default=6, ge=1)
    epochs_finetune: int = Field(default=18, ge=1)
    patience: int = Field(default=6, ge=1)
    head_lr: float = Field(default=8e-4, gt=0)
    finetune_lr: float = Field(default=2e-5, gt=0)
    weight_decay: float = Field(default=0.03, ge=0)
    label_smoothing: float = Field(default=0.07, ge=0, lt=1)


class VisionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BIOSENTINELLE_VISION_", env_nested_delimiter="__", extra="forbid"
    )
    dataset_root: Path = Path("data/datasets")
    output_root: Path = Path("data/results/vision")
    checkpoint_root: Path = Path("data/checkpoints")
    gpu_lock_path: Path = Path("data/results/.vision-gpu.lock")
    classes_manifest: Path | None = None
    detector_weights: Path | None = None
    classifier_checkpoint: Path | None = None
    train_manifest: Path | None = None
    initial_checkpoint: Path | None = None
    inbox_root: Path = Path("data/datasets/inbox")
    analysis_video: str = ""
    analysis_force: bool = False
    watch_poll_seconds: float = Field(default=2, gt=0, allow_inf_nan=False)
    watch_stable_seconds: float = Field(default=10, ge=0, allow_inf_nan=False)
    device: Literal["cpu", "cuda"] = "cpu"
    seed: int = 42
    detection_threshold: float = Field(default=0.10, ge=0.005, le=1)
    classification_threshold: float = Field(default=0.48, ge=0, le=1)
    infer_every_n_frames: int = Field(default=2, ge=1)
    frames: FramesConfig = Field(default_factory=FramesConfig)
    crops: CropsConfig = Field(default_factory=CropsConfig)
    split: SplitConfig = Field(default_factory=SplitConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
