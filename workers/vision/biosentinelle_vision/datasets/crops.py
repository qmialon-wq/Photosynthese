import hashlib
from io import BytesIO

from PIL import Image
from PIL.Image import Image as PILImage

from ..config import CropsConfig
from ..schemas import Box, CropRecord, DetectionsManifest
from ..storage.base import Storage


def crop_image(image: PILImage, box: Box, config: CropsConfig) -> PILImage | None:
    width, height = image.size
    left = max(0, int((box.x - box.w * config.margin) * width))
    top = max(0, int((box.y - box.h * config.margin) * height))
    right = min(width, int((box.x + box.w * (1 + config.margin)) * width))
    bottom = min(height, int((box.y + box.h * (1 + config.margin)) * height))
    if right - left < config.min_side or bottom - top < config.min_side:
        return None
    return image.convert("RGB").crop((left, top, right, bottom))


def save_crop(image: PILImage, storage: Storage, key: str) -> None:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=93)
    storage.write_bytes(key, buffer.getvalue())


def build_crops(
    source: DetectionsManifest,
    storage: Storage,
    config: CropsConfig,
) -> tuple[CropRecord, ...]:
    records = []
    for item in source.frames:
        if item.error:
            continue
        with Image.open(BytesIO(storage.read_bytes(item.frame.image_key))) as image:
            for detection in sorted(item.detections, key=lambda d: d.confidence, reverse=True)[
                : config.max_per_frame
            ]:
                crop = crop_image(image, detection.box, config)
                if crop is None:
                    continue
                identity = (
                    item.frame.image_key
                    + source.detector_identity
                    + detection.box.model_dump_json()
                )
                crop_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
                key = f"crops/{crop_id}.jpg"
                save_crop(crop, storage, key)
                records.append(
                    CropRecord(
                        crop_id=crop_id,
                        image_key=key,
                        frame=item.frame,
                        box=detection.box,
                        detection_confidence=detection.confidence,
                    )
                )
    storage.write_json(
        "crops.json",
        {
            "schema_version": "1",
            "class_manifest_version": source.class_manifest_version,
            "crops": [record.model_dump(mode="json") for record in records],
        },
    )
    return tuple(records)
