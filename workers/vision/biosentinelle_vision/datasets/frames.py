import math
from pathlib import Path

from ..config import FramesConfig
from ..errors import VideoError
from ..schemas import FrameRecord, FramesManifest, Inventory, ProcessingIssue
from ..storage import LocalStorage
from .inventory import file_hash, video_metadata


def sample_indices(count: int, fps: float, config: FramesConfig) -> tuple[int, ...]:
    if count <= 0 or not math.isfinite(fps) or fps <= 0:
        raise VideoError("Nombre d'images/FPS invalide")
    step = max(1, math.ceil(fps * config.min_seconds_between))
    slots = (count - 1) // step + 1
    n = min(config.max_per_video, slots)
    if n == 1:
        return (0,)
    return tuple((i * (slots - 1) // (n - 1)) * step for i in range(n))


def extract_frames(
    source: Inventory,
    storage: LocalStorage,
    config: FramesConfig,
    *,
    manifest_key: str = "frames.json",
) -> FramesManifest:
    import cv2

    records, issues = [], []
    root = Path(source.dataset_root).resolve()
    for video in source.videos:
        path = (root / video.relative_path).resolve()
        cap = None
        try:
            if video.error:
                raise VideoError(video.error)
            if not path.is_relative_to(root):
                raise VideoError("Chemin vidéo hors dataset")
            if video.content_hash and file_hash(path) != video.content_hash:
                raise VideoError("Vidéo modifiée depuis l'inventaire ; refaire l'inventaire")
            cap = cv2.VideoCapture(str(path))
            fps, count, _, _ = video_metadata(cap, path)
            for index in sample_indices(count, fps, config):
                if not cap.set(cv2.CAP_PROP_POS_FRAMES, index):
                    raise VideoError(f"Positionnement impossible à l'image {index}")
                ok, image = cap.read()
                if not ok:
                    raise VideoError(f"Image {index} illisible")
                ok, encoded = cv2.imencode(
                    ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, config.jpeg_quality]
                )
                if not ok:
                    raise VideoError(f"Encodage JPEG impossible à l'image {index}")
                key = f"frames/{video.video_id}/{index:07d}.jpg"
                storage.write_bytes(key, encoded.tobytes())
                records.append(
                    FrameRecord(
                        video_id=video.video_id,
                        group_id=video.group_id or video.video_id,
                        frame_index=index,
                        time_seconds=index / fps,
                        image_key=key,
                        species_candidate=video.species_candidate,
                        split=video.split,
                    )
                )
        except (OSError, VideoError, cv2.error) as exc:
            issues.append(ProcessingIssue(source=video.relative_path, message=str(exc)))
        finally:
            if cap is not None:
                cap.release()
    result = FramesManifest(
        class_manifest_version=source.class_manifest_version,
        frames=tuple(records),
        issues=tuple(issues),
    )
    storage.write_json(manifest_key, result.model_dump(mode="json"))
    return result
