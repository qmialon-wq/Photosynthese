from collections.abc import Sequence
from io import BytesIO

from PIL import Image

from ..classes import ClassManifest
from ..config import CropsConfig
from ..errors import ManifestError
from ..schemas import Box, CropRecord
from ..storage.base import Storage
from .crops import crop_image, save_crop


def apply_review(
    records: Sequence[CropRecord],
    crop_id: str,
    *,
    accept: bool,
    label: str | None,
    box: Box | None,
    classes: ClassManifest,
    storage: Storage,
    config: CropsConfig,
) -> tuple[CropRecord, ...]:
    matches = [r for r in records if r.crop_id == crop_id]
    if len(matches) != 1:
        raise ManifestError("Crop absent ou identifiant dupliqué")
    record = matches[0]
    if accept:
        if label not in classes.names:
            raise ManifestError("Une espèce valide est requise pour accepter le crop")
        corrected_box = box or record.box
        with Image.open(BytesIO(storage.read_bytes(record.frame.image_key))) as image:
            crop = crop_image(image, corrected_box, config)
        if crop is None:
            raise ManifestError("Recadrage corrigé trop petit")
        # Conserver le crop brut ; la revue écrit une version distincte.
        image_key = f"reviewed/{crop_id}.jpg"
        save_crop(crop, storage, image_key)
        updated = record.model_copy(
            update={
                "review": "accept",
                "label": label,
                "box": corrected_box,
                "image_key": image_key,
            }
        )
    else:
        updated = record.model_copy(update={"review": "reject", "label": None})
    result = tuple(updated if r.crop_id == crop_id else r for r in records)
    storage.write_json(
        "review.json",
        {
            "schema_version": "1",
            "class_manifest_version": classes.version,
            "crops": [r.model_dump(mode="json") for r in result],
        },
    )
    return result
