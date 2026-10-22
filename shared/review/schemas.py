from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.vision_jobs import AnalysisRequest

Split = Literal["train", "val", "test"]
State = Literal["pending", "validated", "corrected", "rejected"]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Box(Schema):
    x: Probability
    y: Probability
    w: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    h: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def inside(self) -> "Box":
        if self.x + self.w > 1.000001 or self.y + self.h > 1.000001:
            raise ValueError("Bounding box hors image")
        return self


class ImportVideo(Schema):
    video: str = Field(min_length=1, max_length=1024)
    group_id: str | None = Field(default=None, min_length=1, max_length=128)
    split: Split | None = None
    classify: bool = False

    @model_validator(mode="after")
    def path(self) -> "ImportVideo":
        AnalysisRequest(video=self.video)
        return self


class Decision(Schema):
    expected_revision: int = Field(ge=0)
    decision: Literal["validate", "reject", "reopen"]
    label: str | None = Field(default=None, min_length=1, max_length=80)
    box: Box | None = None
    reason: str = Field(default="", max_length=1000)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def corrections_require_validation(self) -> "Decision":
        if self.decision != "validate" and (self.label is not None or self.box is not None):
            raise ValueError("Une correction de label ou boîte exige decision=validate")
        return self


class BatchItem(Schema):
    sample_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)


class BatchDecision(Schema):
    items: list[BatchItem] = Field(min_length=1, max_length=100)
    decision: Literal["validate", "reject"]
    label: str | None = Field(default=None, min_length=1, max_length=80)
    reason: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def explicit_selection(self) -> "BatchDecision":
        if len({item.sample_id for item in self.items}) != len(self.items):
            raise ValueError("Un recadrage ne peut figurer deux fois dans le lot")
        if self.decision == "validate" and self.label is None:
            raise ValueError("Choisir explicitement une espèce pour le lot")
        if self.decision == "reject" and self.label is not None:
            raise ValueError("Un rejet ne peut attribuer une espèce")
        return self


class DatasetRequest(Schema):
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    exclude_groups: tuple[str, ...] = ()
    exclude_quality: tuple[Literal["blurry", "too_small", "near_duplicate"], ...] = ()


class Operation(Schema):
    id: str
    status: Literal["queued", "running", "completed", "error"]
    status_url: str
