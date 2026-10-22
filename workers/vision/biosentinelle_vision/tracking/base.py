from collections.abc import Sequence
from typing import Any, Protocol

from ..schemas import Detection, Prediction, Record


class Observation(Record):
    detection: Detection
    prediction: Prediction | None = None


class TrackedObservation(Record):
    observation: Observation
    track_id: int


class Tracker(Protocol):
    def update(
        self,
        observations: Sequence[Observation],
        timestamp: float,
    ) -> tuple[TrackedObservation, ...]: ...

    def summaries(self) -> list[dict[str, Any]]: ...

    def metrics(self) -> dict[str, Any]: ...
