import hashlib
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from ..config import CropsConfig
from ..datasets.crops import crop_image
from ..schemas import Box
from ..storage import LocalStorage

QUALITY_VERSION = "laplacian-dhash-v1"


def quality(image: Image.Image) -> dict[str, Any]:
    import cv2

    gray = np.asarray(image.convert("L"))
    small = np.asarray(image.convert("L").resize((9, 8)), dtype=np.int16)
    bits = small[:, 1:] > small[:, :-1]
    digest = sum(int(bit) << index for index, bit in enumerate(bits.flatten()))
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    thumb = np.asarray(image.convert("L").resize((16, 16)), dtype=np.uint8)
    return {
        "version": QUALITY_VERSION,
        "blurry": variance < 50,
        "too_small": min(image.size) < 28,
        "near_duplicate": False,
        "laplacian_variance": variance,
        "dhash": f"{digest:016x}",
        "thumbnail": thumb.tobytes().hex(),
        "width": image.width,
        "height": image.height,
        "thresholds": {"blur_variance": 50, "min_side": 28, "hamming": 4, "pixel_mad": 8},
    }


def similar(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first.get("version") != QUALITY_VERSION or second.get("version") != QUALITY_VERSION:
        return False
    distance = (int(first["dhash"], 16) ^ int(second["dhash"], 16)).bit_count()
    a = np.frombuffer(bytes.fromhex(first["thumbnail"]), dtype=np.uint8).astype(np.int16)
    b = np.frombuffer(bytes.fromhex(second["thumbnail"]), dtype=np.uint8).astype(np.int16)
    return distance <= 4 and float(np.abs(a - b).mean()) <= 8


def blob(storage: LocalStorage, data: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(data).hexdigest()
    key = f"review/blobs/{digest}.jpg"
    path = storage.path(key)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Blob corrompu : {key}")
    else:
        storage.write_bytes(key, data)
    return key, digest


def render(
    storage: LocalStorage, original: str, box: dict[str, float], recipe: dict[str, Any]
) -> dict[str, Any]:
    with Image.open(storage.path(original)) as image:
        crop = crop_image(image, Box(**box), CropsConfig(min_side=1, margin=recipe["margin"]))
        if crop is None:
            raise ValueError("Boîte sans pixel exploitable")
        buffer = BytesIO()
        crop.save(buffer, format="JPEG", quality=recipe["jpeg_quality"])
        key, digest = blob(storage, buffer.getvalue())
        return {"crop_key": key, "crop_sha256": digest, "quality": quality(crop)}
