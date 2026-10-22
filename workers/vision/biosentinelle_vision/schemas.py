from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Split = Literal["train", "val", "test"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Box(Record):
    x: Probability
    y: Probability
    w: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    h: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def inside_image(self) -> "Box":
        if self.x + self.w > 1.000001 or self.y + self.h > 1.000001:
            raise ValueError("Boîte hors image")
        return self


class Detection(Record):
    box: Box
    confidence: Probability


class Prediction(Record):
    probabilities: tuple[Probability, ...]
    label: str | None

    @model_validator(mode="after")
    def distribution(self) -> "Prediction":
        if not self.probabilities or abs(sum(self.probabilities) - 1) > 1e-4:
            raise ValueError("Probabilités non normalisées")
        return self


class VideoRecord(Record):
    video_id: str
    relative_path: str
    content_hash: str | None = None
    species_candidate: str | None = None
    candidates: tuple[str, ...] = ()
    error: str | None = None
    group_id: str | None = None
    split: Split | None = None
    multispecies: bool | None = None


class Inventory(Record):
    schema_version: Literal["1"] = "1"
    class_manifest_version: str
    dataset_root: str
    videos: tuple[VideoRecord, ...]


class FrameRecord(Record):
    video_id: str
    group_id: str
    frame_index: int = Field(ge=0)
    time_seconds: float = Field(ge=0, allow_inf_nan=False)
    image_key: str
    species_candidate: str | None = None
    split: Split | None = None


class ProcessingIssue(Record):
    source: str
    message: str


class FramesManifest(Record):
    schema_version: Literal["1"] = "1"
    class_manifest_version: str
    frames: tuple[FrameRecord, ...]
    issues: tuple[ProcessingIssue, ...] = ()


class FrameDetections(Record):
    frame: FrameRecord
    detections: tuple[Detection, ...] = ()
    error: str | None = None


class DetectionsManifest(Record):
    schema_version: Literal["1"] = "1"
    class_manifest_version: str
    detector_identity: str
    frames: tuple[FrameDetections, ...]


class CropRecord(Record):
    crop_id: str
    image_key: str
    frame: FrameRecord
    box: Box
    detection_confidence: Probability
    review: Literal["pending", "accept", "reject"] = "pending"
    label: str | None = None


class LabeledPrediction(Record):
    crop_id: str
    video_id: str
    truth: str
    human_validated: bool
    probabilities: tuple[Probability, ...]


class CropsManifest(Record):
    schema_version: Literal["1"] = "1"
    class_manifest_version: str
    crops: tuple[CropRecord, ...]


class PredictionsManifest(Record):
    schema_version: Literal["1"] = "1"
    class_manifest_version: str
    classes: tuple[str, ...]
    predictions: tuple[LabeledPrediction, ...]
    # Une vérité unique seulement si une personne l'a réellement validée pour la vidéo.
    video_truth: dict[str, str] = Field(default_factory=dict)
