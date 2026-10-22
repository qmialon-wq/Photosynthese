import os
from pathlib import Path

import pytest
from biosentinelle_vision.classes import load_classes
from biosentinelle_vision.classification.model import TorchClassifier
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.detection.megadetector import MegaDetector, api_diagnostics
from biosentinelle_vision.detection.weights import fetch_weights, verify_weights
from biosentinelle_vision.inference.render import draw_detections
from biosentinelle_vision.inference.video import _analyze_video
from biosentinelle_vision.storage import LocalStorage
from biosentinelle_vision.storage.gpu import exclusive_gpu
from biosentinelle_vision.tracking.iou import IoUTracker
from PIL import Image

pytestmark = pytest.mark.real_model


def test_real_video_and_downloaded_models(tmp_path: Path):
    video_name = os.getenv("BIOSENTINELLE_REAL_VIDEO")
    if not video_name:
        pytest.skip("Définir BIOSENTINELLE_REAL_VIDEO pour activer cette intégration")
    settings = VisionSettings()
    assert settings.detector_weights is not None
    if os.getenv("BIOSENTINELLE_REAL_DOWNLOAD") == "1":
        fetch_weights(settings.detector_weights)
    verify_weights(settings.detector_weights)
    assert api_diagnostics()["package_version"] == "10.0.28"
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        _real_pipeline(video_name, settings, tmp_path)


def _real_pipeline(video_name: str, settings: VisionSettings, tmp_path: Path) -> None:
    classes = load_classes()
    detector = MegaDetector(settings.detector_weights, settings)
    assert settings.classifier_checkpoint is not None
    classifier = TorchClassifier(
        settings.classifier_checkpoint,
        classes,
        device=settings.device,
        threshold=settings.classification_threshold,
    )
    storage = LocalStorage(Path(os.getenv("BIOSENTINELLE_REAL_OUTPUT", str(tmp_path))))
    report = _analyze_video(
        Path(video_name),
        detector,
        classifier,
        IoUTracker(classes, settings.tracking),
        classes,
        storage,
        settings,
        "annotated/video.mp4",
        "video_report.json",
    )
    assert report["frames_decoded"] > 0
    assert storage.path(report["annotated_key"]).is_file()
    assert len(report["frames"]) == report["diagnostics"]["frames_analyzed"]
    # Utiliser une image réellement extraite de la vidéo, sans supposer un animal présent.
    import cv2

    cap = cv2.VideoCapture(video_name)
    try:
        ok, frame = cap.read()
        assert ok
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
    detections = detector.detect(image)
    draw_detections(image, detections).save(storage.path("detector-image.jpg"))
    for frame in report["frames"]:
        for detection in frame["detections"]:
            assert 0 <= detection["detection_score"] <= 1
            if detection["classification"]:
                assert len(detection["classification"]["probabilities"]) == 10
