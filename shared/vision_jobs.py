"""Contrat API/worker et file Redis Streams avec acquittement après traitement."""

import json
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from redis import Redis

STREAM = "biosentinelle:vision:jobs"
GROUP = "vision"
CONSUMER = "vision-single"


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    video: str = Field(min_length=1, max_length=1024)
    detection_only: bool = False
    detection_threshold: float = Field(default=0.10, ge=0.005, le=1, allow_inf_nan=False)
    classification_threshold: float = Field(default=0.48, ge=0, le=1, allow_inf_nan=False)
    track_threshold: float = Field(default=0.60, ge=0, le=1, allow_inf_nan=False)
    track_min_hits: int = Field(default=2, ge=1)
    infer_every_n_frames: int = Field(default=2, ge=1)
    force: bool = False

    @field_validator("video")
    @classmethod
    def relative_video(cls, value: str) -> str:
        if (
            "\\" in value
            or "\x00" in value
            or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).drive
            or ".." in PurePosixPath(value).parts
        ):
            raise ValueError("Fournir un chemin relatif à inbox, avec des séparateurs /")
        return value


class TrainingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["train_classifier", "evaluate_classifier"] = "train_classifier"
    split: Literal["train", "val", "test"] = "test"
    configuration: dict[str, Any]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["review"] = "review"
    operation_id: str


class ConsoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["console"] = "console"
    task_id: str


class JobStore:
    def __init__(self, client: Redis) -> None:
        self.client = client

    @staticmethod
    def key(job_id: str) -> str:
        return f"biosentinelle:vision:job:{job_id}"

    def enqueue(
        self, request: AnalysisRequest | TrainingRequest | ReviewRequest | ConsoleRequest
    ) -> dict[str, Any]:
        job = {
            "id": str(uuid4()),
            "status": "queued",
            "kind": request.kind
            if isinstance(request, TrainingRequest | ReviewRequest | ConsoleRequest)
            else "analysis",
            "request": request.model_dump(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        if isinstance(request, TrainingRequest):
            training = job["request"]["configuration"].setdefault("training", {})
            training["run_id"] = training.get("run_id") or job["id"]
        with self.client.pipeline(transaction=True) as pipeline:
            pipeline.set(self.key(job["id"]), json.dumps(job))
            pipeline.xadd(STREAM, {"id": job["id"]})
            pipeline.execute()
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        value = self.client.get(self.key(job_id))
        return json.loads(value) if value else None

    def save(self, job: dict[str, Any]) -> None:
        self.client.set(self.key(job["id"]), json.dumps(job, ensure_ascii=False, allow_nan=False))

    def finish(self, message_id: str, job: dict[str, Any]) -> None:
        with self.client.pipeline(transaction=True) as pipeline:
            pipeline.set(self.key(job["id"]), json.dumps(job, ensure_ascii=False, allow_nan=False))
            pipeline.xack(STREAM, GROUP, message_id)
            pipeline.xdel(STREAM, message_id)
            pipeline.execute()
