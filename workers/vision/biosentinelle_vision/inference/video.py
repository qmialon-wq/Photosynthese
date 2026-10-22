import os
import time
import uuid
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from ..classes import ClassManifest
from ..classification.base import Classifier
from ..classification.model import prediction_from_probabilities
from ..config import VisionSettings
from ..datasets.crops import crop_image
from ..datasets.inventory import video_metadata
from ..detection.base import Detector
from ..errors import ModelError, VideoError
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from ..tracking.base import Observation, TrackedObservation, Tracker
from .render import draw_tracks


class InferenceTimer:
    """Temps muraux et durée CUDA synchronisée des appels, sans imports GPU sur CPU."""

    def __init__(self, device: str) -> None:
        self.device = device
        self.seconds: Counter[str] = Counter()
        self.gpu_seconds = 0.0 if device == "cuda" else None

    def call(self, name: str, function: Callable[[], Any]) -> Any:
        if self.device == "cuda":
            import torch

            start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            start.record()
        begin = time.perf_counter()
        result = function()
        if self.device == "cuda":
            end.record()
            end.synchronize()
            self.gpu_seconds += start.elapsed_time(end) / 1000
        self.seconds[name] += time.perf_counter() - begin
        return result


def analyze_video(
    video: Path,
    detector: Detector,
    classifier: Classifier | None,
    tracker: Tracker,
    classes: ClassManifest,
    storage: LocalStorage,
    settings: VisionSettings,
    *,
    output_key: str = "annotated/video.mp4",
    report_key: str = "video_report.json",
    shadow_classifier: Classifier | None = None,
) -> dict[str, Any]:
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        return _analyze_video(
            video,
            detector,
            classifier,
            tracker,
            classes,
            storage,
            settings,
            output_key,
            report_key,
            shadow_classifier=shadow_classifier,
        )


def _analyze_video(
    video: Path,
    detector: Detector,
    classifier: Classifier | None,
    tracker: Tracker,
    classes: ClassManifest,
    storage: LocalStorage,
    settings: VisionSettings,
    output_key: str,
    report_key: str,
    progress: Callable[[int, int], None] | None = None,
    *,
    shadow_classifier: Classifier | None = None,
    shadow_error: str | None = None,
) -> dict[str, Any]:
    import cv2

    if classifier is None and not settings.detection_only:
        raise ModelError(
            "Classificateur absent ; activer explicitement detection_only pour détecter seul"
        )
    if classifier is not None and classifier.classes != classes.names:
        raise ModelError("Classes du classificateur incompatibles")
    if tracker.summaries():
        raise ModelError("Un tracker neuf est requis pour chaque vidéo")
    target = storage.path(output_key)
    if target.suffix.lower() != ".mp4" or target == video.resolve():
        raise VideoError("La sortie doit être un autre fichier MP4")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.stem}-{uuid.uuid4().hex}.mp4")
    cap, writer = cv2.VideoCapture(str(video)), None
    frame_count, observed_tracks, frames = 0, [], []
    tracked: tuple[TrackedObservation, ...] = ()
    counts: Counter[str] = Counter()
    timer, began = InferenceTimer(settings.device), time.perf_counter()
    shadow_timer = InferenceTimer("cpu")
    shadow_metadata = getattr(shadow_classifier, "metadata", None)
    try:
        fps, expected_count, width, height = video_metadata(cap, video)
        writer = cv2.VideoWriter(
            str(temporary), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            raise VideoError("Impossible d'ouvrir l'encodeur vidéo MP4")
        while True:
            if progress:
                progress(frame_count, expected_count)
            ok, frame = cap.read()
            if not ok:
                break
            if frame.shape[:2] != (height, width):
                raise VideoError("Dimensions d'image variables dans la vidéo")
            if frame_count % settings.infer_every_n_frames == 0:
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detections = tuple(
                    d
                    for d in timer.call("detector", lambda image=image: detector.detect(image))
                    if d.confidence >= settings.detection_threshold
                )
                counts["frames_analyzed"] += 1
                counts["frames_with_detection"] += bool(detections)
                counts["detections"] += len(detections)
                crops, crop_indices, reasons = [], [], {}
                for index, detection in enumerate(detections):
                    if index >= settings.crops.max_per_frame:
                        reasons[index] = "crop_limit"
                        continue
                    crop = crop_image(image, detection.box, settings.crops)
                    if crop is None:
                        reasons[index] = "crop_too_small"
                    else:
                        crop_indices.append(index)
                        crops.append(crop)
                counts["valid_crops"] += len(crops)
                predictions = (
                    timer.call("classifier", lambda crops=crops: classifier.predict(crops))
                    if crops and classifier is not None
                    else ()
                )
                if classifier is not None and len(predictions) != len(crops):
                    raise ModelError("Le classificateur ne retourne pas une prédiction par crop")
                classified = {
                    index: prediction_from_probabilities(
                        prediction.probabilities, classes, settings.classification_threshold
                    )
                    for index, prediction in zip(
                        crop_indices, predictions, strict=classifier is not None
                    )
                }
                counts["predictions"] += len(predictions)
                shadow_predictions = []
                if crops and shadow_classifier is not None:
                    try:
                        if shadow_classifier.classes != classes.names:
                            raise ModelError("Référentiel du modèle shadow incompatible")
                        shadow_batch = shadow_timer.call(
                            "shadow_classifier",
                            lambda model=shadow_classifier, batch=crops: model.predict(batch),
                        )
                        if len(shadow_batch) != len(crops):
                            raise ModelError("Nombre de prédictions shadow incompatible")
                        shadow_predictions = [
                            {
                                "detection_index": i,
                                "label": p.label,
                                "probabilities": p.probabilities,
                            }
                            for i, p in zip(crop_indices, shadow_batch, strict=True)
                        ]
                    except Exception as exc:
                        shadow_error = f"{type(exc).__name__}: {exc}"
                        shadow_classifier = None
                observations = [
                    Observation(detection=d, prediction=classified.get(i))
                    for i, d in enumerate(detections)
                ]
                tracked = tracker.update(observations, frame_count / fps)
                if tuple(t.observation for t in tracked) != tuple(observations) or len(
                    {t.track_id for t in tracked}
                ) != len(observations):
                    raise ModelError("Le tracker doit associer chaque observation une seule fois")
                observed_tracks.append([item.track_id for item in tracked])
                localized = []
                for index, item in enumerate(tracked):
                    prediction = item.observation.prediction
                    state = (
                        "detection_unclassified"
                        if prediction is None
                        else ("species_recognized" if prediction.label else "species_uncertain")
                    )
                    counts[state] += 1
                    localized.append(
                        {
                            "box": item.observation.detection.box.model_dump(),
                            "detection_score": item.observation.detection.confidence,
                            "track_id": item.track_id,
                            "state": state,
                            "classification": None
                            if prediction is None
                            else {
                                "label": prediction.label,
                                "score": max(prediction.probabilities),
                                "probabilities": dict(
                                    zip(classes.names, prediction.probabilities, strict=True)
                                ),
                            },
                            "unclassified_reason": reasons.get(index, "classifier_not_configured")
                            if prediction is None
                            else None,
                        }
                    )
                frames.append(
                    {
                        "frame_index": frame_count,
                        "time_seconds": frame_count / fps,
                        "state": "no_detection" if not detections else "animals_detected",
                        "detections": localized,
                        **(
                            {"shadow_predictions": shadow_predictions} if shadow_predictions else {}
                        ),
                    }
                )
            # Maintien visuel uniquement : aucune inférence ni mise à jour du tracker
            # entre deux images analysées. Une analyse vide efface aussi le cadre.
            draw_tracks(frame, tracked)
            writer.write(frame)
            frame_count += 1
        if not frame_count or frame_count < expected_count:
            raise VideoError(f"Décodage incomplet : {frame_count}/{expected_count} images")
        writer.release()
        writer = None
        if not temporary.is_file() or not temporary.stat().st_size:
            raise VideoError("Export vidéo vide")
        os.replace(temporary, target)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        temporary.unlink(missing_ok=True)
    tracks = tracker.summaries()
    labels = {track["track_id"]: track["label"] for track in tracks}
    species_counts = Counter(label for label in labels.values() if label is not None)
    simultaneous: Counter[str] = Counter()
    for frame_tracks in observed_tracks:
        visible = Counter(labels[t] for t in frame_tracks if labels[t] is not None)
        for label, count in visible.items():
            simultaneous[label] = max(simultaneous[label], count)
    status = (
        "no_detection"
        if not counts["detections"]
        else (
            "species_recognized"
            if species_counts
            else "species_uncertain"
            if counts["predictions"]
            else "detection_unclassified"
        )
    )
    report = {
        "schema_version": "2",
        "class_manifest_version": classes.version,
        "video": str(video.resolve()),
        "annotated_key": output_key,
        "fps": fps,
        "width": width,
        "height": height,
        "frames_decoded": frame_count,
        "detections": counts["detections"],
        "sample_every_n_frames": settings.infer_every_n_frames,
        "annotation_display": "hold_last_analysis",
        "detector_identity": detector.identity,
        "models": {
            "detector_api": getattr(detector, "diagnostics", None),
            "classifier": getattr(classifier, "metadata", None),
            "shadow": shadow_metadata,
        },
        "thresholds": {
            "detection": settings.detection_threshold,
            "classification": settings.classification_threshold,
            "track_confidence": settings.tracking.confidence_threshold,
            "track_min_hits": settings.tracking.min_hits,
            "association_iou": settings.tracking.iou_threshold,
        },
        "frames": frames,
        "tracks": tracks,
        "tracking_metrics": tracker.metrics(),
        "diagnostics": {
            **{
                k: counts[k]
                for k in (
                    "frames_analyzed",
                    "frames_with_detection",
                    "valid_crops",
                    "predictions",
                    "species_recognized",
                    "species_uncertain",
                    "detection_unclassified",
                )
            },
            "total_seconds": time.perf_counter() - began,
            "detector_seconds": timer.seconds["detector"],
            "classifier_seconds": timer.seconds["classifier"],
            "shadow_classifier_seconds": shadow_timer.seconds["shadow_classifier"],
            "shadow_error": shadow_error,
            "gpu_elapsed_seconds": timer.gpu_seconds,
            "gpu_timing_method": "cuda_events_elapsed"
            if settings.device == "cuda"
            else "not_applicable",
        },
        "species": [
            {
                "species": s.name,
                "latin": s.latin,
                "estimated_tracks": species_counts[s.name],
                "estimated_maximum_simultaneous": simultaneous[s.name],
            }
            for s in classes.classes
            if species_counts[s.name]
        ],
        "status": status,
        "warning": "Les pistes sont des estimations, pas des individus uniques garantis",
    }
    storage.write_json(report_key, report)
    storage.write_json(
        str(Path(report_key).with_name("statistics.json")),
        {
            "status": status,
            "frames_decoded": frame_count,
            "detections": counts["detections"],
            "diagnostics": report["diagnostics"],
            "tracking_metrics": report["tracking_metrics"],
            "species": report["species"],
        },
    )
    return report
