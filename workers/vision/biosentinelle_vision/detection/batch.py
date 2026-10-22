import logging
from io import BytesIO

from PIL import Image

from ..schemas import DetectionsManifest, FrameDetections, FramesManifest
from ..storage.base import Storage
from .base import Detector


def detect_frames(
    source: FramesManifest,
    detector: Detector,
    storage: Storage,
    *,
    manifest_key: str = "detections.json",
) -> DetectionsManifest:
    results = []
    for index, frame in enumerate(source.frames, start=1):
        try:
            with Image.open(BytesIO(storage.read_bytes(frame.image_key))) as image:
                detections = detector.detect(image.convert("RGB"))
            results.append(FrameDetections(frame=frame, detections=detections))
        except Exception as exc:
            results.append(FrameDetections(frame=frame, error=f"{type(exc).__name__}: {exc}"))
        if index == 1 or index % 100 == 0 or index == len(source.frames):
            logging.getLogger(__name__).info("Détection : %s/%s images", index, len(source.frames))
    result = DetectionsManifest(
        class_manifest_version=source.class_manifest_version,
        detector_identity=detector.identity,
        frames=tuple(results),
    )
    storage.write_json(manifest_key, result.model_dump(mode="json"))
    return result
