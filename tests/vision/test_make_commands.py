import json
import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from biosentinelle_vision import commands
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.cli import main
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.errors import GpuBusyError, ManifestError, ModelError, VideoError
from biosentinelle_vision.schemas import Box, CropRecord, CropsManifest, FrameRecord
from PIL import Image

from .test_video_and_gpu_lock import ClassifierFixture, DetectorFixture


def reviewed_dataset(root: Path, classes: ClassManifest) -> tuple[VisionSettings, CropsManifest]:
    crops = []
    for split in ("train", "val"):
        for index, name in enumerate(classes.names):
            key = f"reviewed/{split}-{index}.png"
            path = root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (48, 48), "white").save(path)
            frame = FrameRecord(
                video_id=f"{split}-{index}",
                group_id=f"{split}-{index}",
                frame_index=0,
                time_seconds=0,
                image_key=key,
                split=split,
            )
            crops.append(
                CropRecord(
                    crop_id=f"{split}-{index}",
                    image_key=key,
                    frame=frame,
                    box=Box(x=0, y=0, w=1, h=1),
                    detection_confidence=0.9,
                    label=name,
                    review="accept",
                )
            )
    manifest = CropsManifest(class_manifest_version=classes.version, crops=tuple(crops))
    (root / "review.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    return VisionSettings(output_root=root), manifest


def test_training_preflight_without_torch(tmp_path: Path, classes: ClassManifest) -> None:
    with pytest.raises(ManifestError, match="revue absent"):
        commands.training_samples(VisionSettings(output_root=tmp_path), classes)
    settings, manifest = reviewed_dataset(tmp_path, classes)
    assert len(commands.training_samples(settings, classes)) == 20
    assert (
        main(
            [
                "train",
                "--manifest",
                str(tmp_path / "review.json"),
                "--storage-root",
                str(tmp_path),
                "--check-only",
            ]
        )
        == 0
    )
    weak = manifest.model_copy(
        update={
            "crops": tuple(
                r.model_copy(update={"review": "pending", "label": None}) for r in manifest.crops
            )
        }
    )
    (tmp_path / "review.json").write_text(weak.model_dump_json(), encoding="utf-8")
    with pytest.raises(ManifestError, match="sans train validé"):
        commands.training_samples(settings, classes)


def analysis_settings(tmp_path: Path, inbox: Path) -> VisionSettings:
    detector, classifier = tmp_path / "detector.pt", tmp_path / "classifier.pt"
    # Identités de fixtures, jamais chargées comme des poids ML.
    detector.write_bytes(b"fixture detector identity")
    classifier.write_bytes(b"fixture classifier identity")
    return VisionSettings(
        inbox_root=inbox,
        output_root=tmp_path / "output",
        detector_weights=detector,
        classifier_checkpoint=classifier,
    )


def test_analyze_idempotence_and_model_change(
    tmp_path: Path,
    make_video: Callable,
    classes: ClassManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = make_video("ma video.avi")
    settings = analysis_settings(tmp_path, video.parent)
    calls = []

    def load(*args: object) -> tuple[DetectorFixture, ClassifierFixture]:
        calls.append(True)
        return DetectorFixture(), ClassifierFixture(classes)

    monkeypatch.setattr(commands, "_load_models", load)
    first = commands.run_analyses(commands.input_videos(settings), settings, classes)
    assert first[0]["status"] == "completed" and len(calls) == 1
    root = settings.output_root / first[0]["output"]
    assert (root / "annotated.mp4").is_file() and (root / "report.json").is_file()
    again = commands.run_analyses((video,), settings, classes)
    assert again[0]["skipped"] and len(calls) == 1
    assert video.exists()
    settings.classifier_checkpoint.write_bytes(b"different fixture identity")
    changed = commands.run_analyses((video,), settings, classes)
    assert changed[0]["output"] != first[0]["output"] and len(calls) == 2


def test_failure_is_recorded_and_force_retries(
    tmp_path: Path,
    make_video: Callable,
    classes: ClassManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = make_video()
    settings = analysis_settings(tmp_path, video.parent)
    monkeypatch.setattr(
        commands, "_load_models", lambda *a: (DetectorFixture(), ClassifierFixture(classes))
    )

    def fail(*args: object) -> None:
        raise VideoError("fixture read failure")

    monkeypatch.setattr(commands, "_analyze_video", fail)
    result = commands.run_analyses((video,), settings, classes)
    assert result[0]["status"] == "error"
    state = json.loads((settings.output_root / result[0]["output"] / "state.json").read_text())
    assert "fixture read failure" in state["error"]
    assert commands.run_analyses((video,), settings, classes)[0]["skipped"]
    forced = commands.run_analyses(
        (video,), settings.model_copy(update={"analysis_force": True}), classes
    )
    assert not forced[0].get("skipped")


def test_inbox_is_confined_and_weights_are_required(
    tmp_path: Path,
    make_video: Callable,
    classes: ClassManifest,
) -> None:
    video = make_video()
    settings = VisionSettings(inbox_root=video.parent)
    with pytest.raises(ModelError, match="MegaDetector"):
        commands.run_analyses((video,), settings, classes)
    with pytest.raises(VideoError):
        commands.input_videos(settings.model_copy(update={"analysis_video": "../other.mp4"}))
    (video.parent / "copy.mp4.part").write_bytes(b"partial")
    assert commands.input_videos(settings) == (video,)


def test_watch_retries_busy_gpu_and_processes_stable_file_once(
    tmp_path: Path,
    make_video: Callable,
    classes: ClassManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = make_video()
    settings = analysis_settings(tmp_path, video.parent).model_copy(
        update={
            "watch_stable_seconds": 0,
        }
    )
    calls = []

    class Stop:
        turns = 0

        def is_set(self) -> bool:
            return self.turns >= 3

        def wait(self, seconds: float) -> None:
            self.turns += 1

    def run(videos: tuple[Path, ...], *args: object) -> list:
        calls.append(videos)
        if len(calls) == 1:
            raise GpuBusyError("busy fixture")
        return []

    monkeypatch.setattr(commands, "run_analyses", run)
    commands.watch_inbox(settings, classes, Stop())
    assert len(calls) == 2


def test_watch_ignores_unstable_files(
    tmp_path: Path,
    make_video: Callable,
    classes: ClassManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = make_video()
    settings = analysis_settings(tmp_path, video.parent)
    stop = threading.Event()
    monkeypatch.setattr(stop, "wait", lambda seconds: stop.set())
    monkeypatch.setattr(commands, "run_analyses", lambda *a: pytest.fail("Not settled"))
    commands.watch_inbox(settings, classes, stop)
