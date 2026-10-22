import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..classes import ClassManifest
from ..classification.model import prediction_from_probabilities
from ..config import TrackingConfig
from ..schemas import Box
from .base import Observation, TrackedObservation


def iou(a: Box, b: Box) -> float:
    intersection = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x)) * max(
        0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    )
    return intersection / (a.w * a.h + b.w * b.h - intersection)


@dataclass
class Track:
    track_id: int
    box: Box
    votes: list[float]
    first_seconds: float
    last_seconds: float
    hits: int = 0
    classified_hits: int = 0
    misses: int = 0


class IoUTracker:
    def __init__(
        self,
        classes: ClassManifest,
        config: TrackingConfig,
        classification_threshold: float | None = None,
    ) -> None:
        self.classes, self.config = classes, config
        # Ancien argument conservé pour les appelants Python ; les commandes utilisent config.
        self.threshold = (
            config.confidence_threshold
            if classification_threshold is None
            else classification_threshold
        )
        self.updates = 0
        self.matches = 0
        self.tracks: dict[int, Track] = {}
        self.next_id = 1
        self.last_timestamp = -1.0

    def update(
        self,
        observations: Sequence[Observation],
        timestamp: float,
    ) -> tuple[TrackedObservation, ...]:
        if not math.isfinite(timestamp) or timestamp < 0 or timestamp <= self.last_timestamp:
            raise ValueError(
                "Les instants de suivi doivent être strictement croissants et positifs"
            )
        for observation in observations:
            if observation.prediction is None:
                continue
            if len(observation.prediction.probabilities) != len(self.classes.names):
                raise ValueError("Nombre de classes incompatible avec le tracker")
            if observation.prediction.label not in (*self.classes.names, None):
                raise ValueError("Label incompatible avec le tracker")
        self.last_timestamp = timestamp
        self.updates += 1
        pairs = sorted(
            (
                (iou(observation.detection.box, track.box), index, track_id)
                for index, observation in enumerate(observations)
                for track_id, track in self.tracks.items()
                if track.misses <= self.config.max_misses
            ),
            reverse=True,
        )
        assigned: dict[int, int] = {}
        used = set()
        for score, index, track_id in pairs:
            if (
                score >= self.config.iou_threshold
                and index not in assigned
                and track_id not in used
            ):
                assigned[index] = track_id
                used.add(track_id)
                self.matches += 1
        for track_id, track in self.tracks.items():
            if track_id not in used:
                track.misses += 1
        result = []
        for index, observation in enumerate(observations):
            track_id = assigned.get(index)
            if track_id is None:
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = Track(
                    track_id,
                    observation.detection.box,
                    [0.0] * len(self.classes.names),
                    timestamp,
                    timestamp,
                )
            track = self.tracks[track_id]
            track.box, track.last_seconds, track.misses = observation.detection.box, timestamp, 0
            track.hits += 1
            if observation.prediction is not None:
                track.classified_hits += 1
                track.votes = [
                    a + b
                    for a, b in zip(track.votes, observation.prediction.probabilities, strict=True)
                ]
            result.append(TrackedObservation(observation=observation, track_id=track_id))
        return tuple(result)

    def summaries(self) -> list[dict[str, Any]]:
        result = []
        for track in self.tracks.values():
            total = sum(track.votes)
            prediction = (
                prediction_from_probabilities(
                    [value / total for value in track.votes], self.classes, self.threshold
                )
                if total
                else None
            )
            result.append(
                {
                    "track_id": track.track_id,
                    "hits": track.hits,
                    "label": prediction.label
                    if prediction and track.classified_hits >= self.config.min_hits
                    else None,
                    "first_seconds": track.first_seconds,
                    "last_seconds": track.last_seconds,
                    "confidence": max(prediction.probabilities) if prediction else None,
                    "classified_hits": track.classified_hits,
                    "misses": track.misses,
                    "active": track.misses <= self.config.max_misses,
                    "probabilities": prediction.probabilities if prediction else None,
                }
            )
        return result

    def metrics(self) -> dict[str, Any]:
        summaries = self.summaries()
        return {
            "algorithm": "greedy_iou",
            "updates": self.updates,
            "associations": self.matches,
            "tracks_created": len(summaries),
            "tracks_confirmed": sum(t["label"] is not None for t in summaries),
            "tracks_expired": sum(not t["active"] for t in summaries),
            "quality_metrics_available": False,
            "note": "IDF1/MOTA exigent des trajectoires de référence annotées",
        }
