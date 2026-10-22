import hashlib
import math
import re
import unicodedata
from pathlib import Path
from typing import Protocol

from ..classes import ClassManifest
from ..errors import VideoError
from ..schemas import Inventory, VideoRecord

VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".m4v"})


class VideoCaptureMetadata(Protocol):
    def isOpened(self) -> bool: ...

    def get(self, property_id: int) -> float: ...


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return re.sub(r"[^a-z]+", " ", "".join(c for c in text if not unicodedata.combining(c)))


def species_candidates(path: Path, classes: ClassManifest) -> tuple[str, ...]:
    text = " " + normalize(path.stem) + " "
    return tuple(
        species.name
        for species in classes.classes
        if any(" " + normalize(alias) + " " in text for alias in species.aliases)
    )


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def video_metadata(cap: VideoCaptureMetadata, path: Path) -> tuple[float, int, int, int]:
    import cv2

    if not cap.isOpened():
        raise VideoError(f"Vidéo illisible : {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not all(math.isfinite(v) and v > 0 for v in (fps, count, width, height)):
        raise VideoError(f"Métadonnées vidéo invalides : {path}")
    return fps, int(count), int(width), int(height)


def inventory(root: Path, classes: ClassManifest, *, probe: bool = True) -> Inventory:
    import cv2

    root = root.resolve()
    if not root.is_dir():
        raise VideoError(f"Dossier dataset absent : {root}")
    videos = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in VIDEO_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        candidates = species_candidates(path, classes)
        digest, error = None, None
        try:
            if not path.resolve().is_relative_to(root):
                raise VideoError("Lien vidéo hors dataset")
            digest = file_hash(path)
            if probe:
                cap = cv2.VideoCapture(str(path))
                try:
                    video_metadata(cap, path)
                    ok, _ = cap.read()
                    if not ok:
                        raise VideoError("Première image indécodable")
                finally:
                    cap.release()
        except (OSError, VideoError, cv2.error) as exc:
            error = str(exc)
        videos.append(
            VideoRecord(
                video_id=hashlib.sha256(relative.encode()).hexdigest()[:20],
                relative_path=relative,
                content_hash=digest,
                candidates=candidates,
                species_candidate=candidates[0] if len(candidates) == 1 else None,
                group_id=digest,
                error=error,
            )
        )
    return Inventory(
        class_manifest_version=classes.version, dataset_root=str(root), videos=tuple(videos)
    )
