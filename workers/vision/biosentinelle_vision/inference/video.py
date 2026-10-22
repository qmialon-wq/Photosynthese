import os
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from ..classes import ClassManifest
from ..classification.base import Classifier
from ..config import VisionSettings
from ..datasets.crops import crop_image
from ..datasets.inventory import video_metadata
from ..detection.base import Detector
from ..errors import ModelError, VideoError
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from ..tracking.base import Observation, Tracker
from .render import draw_tracks


def analyze_video(
    video: Path,
    detector: Detector,
    classifier: Classifier,
    tracker: Tracker,
    classes: ClassManifest,
    storage: LocalStorage,
    settings: VisionSettings,
    *,
    output_key: str = "annotated/video.mp4",
    report_key: str = "video_report.json",
) -> dict[str, Any]:
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        return _analyze_video(
            video, detector, classifier, tracker, classes, storage, settings, output_key, report_key
        )


def _analyze_video(
    video: Path,
    detector: Detector,
    classifier: Classifier,
    tracker: Tracker,
    classes: ClassManifest,
    storage: LocalStorage,
    settings: VisionSettings,
    output_key: str,
    report_key: str,
) -> dict[str, Any]:
    import cv2

    if classifier.classes != classes.names:
        raise ModelError("Classes du classificateur incompatibles")
    if tracker.summaries():
        raise ModelError("Un tracker neuf est requis pour chaque vidéo")
    target = storage.path(output_key)
    if target.suffix.lower() != ".mp4" or target == video.resolve():
        raise VideoError("La sortie doit être un autre fichier MP4")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.stem}-{uuid.uuid4().hex}.mp4")
    cap, writer = cv2.VideoCapture(str(video)), None
    frame_count, detection_count, observed_tracks = 0, 0, []
    try:
        fps, expected_count, width, height = video_metadata(cap, video)
        writer = cv2.VideoWriter(
            str(temporary), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            raise VideoError("Impossible d'ouvrir l'encodeur vidéo MP4")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame.shape[:2] != (height, width):
                raise VideoError("Dimensions d'image variables dans la vidéo")
            if frame_count % settings.infer_every_n_frames == 0:
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detections = detector.detect(image)
                usable, crops = [], []
                for detection in detections:
                    crop = crop_image(image, detection.box, settings.crops)
                    if crop is not None:
                        usable.append(detection)
                        crops.append(crop)
                predictions = classifier.predict(crops)
                if len(predictions) != len(usable):
                    raise ModelError("Le classificateur ne retourne pas une prédiction par crop")
                observations = [
                    Observation(detection=detection, prediction=prediction)
                    for detection, prediction in zip(usable, predictions, strict=True)
                ]
                tracked = tracker.update(observations, frame_count / fps)
                detection_count += len(detections)
                observed_tracks.append([item.track_id for item in tracked])
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
    counts = Counter(label for label in labels.values() if label is not None)
    simultaneous: Counter[str] = Counter()
    for frame_tracks in observed_tracks:
        visible = Counter(
            labels[track_id] for track_id in frame_tracks if labels[track_id] is not None
        )
        for label, count in visible.items():
            simultaneous[label] = max(simultaneous[label], count)
    report = {
        "schema_version": "1",
        "class_manifest_version": classes.version,
        "video": str(video.resolve()),
        "annotated_key": output_key,
        "fps": fps,
        "frames_decoded": frame_count,
        "detections": detection_count,
        "sample_every_n_frames": settings.infer_every_n_frames,
        "tracks": tracks,
        "species": [
            {
                "species": s.name,
                "latin": s.latin,
                "estimated_tracks": counts[s.name],
                "estimated_maximum_simultaneous": simultaneous[s.name],
            }
            for s in classes.classes
            if counts[s.name]
        ],
        "status": "no_animals_detected"
        if not detection_count
        else "species_identified"
        if counts
        else "animals_detected_species_uncertain",
        "warning": "Les pistes sont des estimations, pas des individus uniques garantis",
    }
    storage.write_json(report_key, report)
    return report
