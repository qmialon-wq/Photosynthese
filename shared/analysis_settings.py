"""Shared typed analysis defaults for single videos and parcel corpora."""

from uuid import UUID

from pydantic import Field

from shared.documents.schemas import Body


class AnalysisOptions(Body):
    parcel_revision: int | None = Field(default=None, gt=0)
    detection_only: bool = False
    detection_threshold: float = Field(default=0.1, ge=0.005, le=1)
    classification_threshold: float = Field(default=0.48, ge=0, le=1)
    track_threshold: float = Field(default=0.6, ge=0, le=1)
    track_min_hits: int = Field(default=2, ge=1, le=100)
    infer_every_n_frames: int = Field(default=2, ge=1, le=1000)
    shadow_model_id: UUID | None = None
