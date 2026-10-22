from collections import Counter, defaultdict
from collections.abc import Sequence
from io import BytesIO
from typing import Any

from PIL import Image

from ..classes import ClassManifest
from ..errors import ManifestError
from ..schemas import CropRecord
from ..storage.base import Storage


def select_samples(
    records: Sequence[CropRecord],
    classes: ClassManifest,
    max_per_video: int = 18,
    *,
    allow_filename_labels: bool = False,
) -> tuple[CropRecord, ...]:
    if max_per_video < 1:
        raise ValueError("Quota par vidéo strictement positif requis")
    if len({record.crop_id for record in records}) != len(records):
        raise ManifestError("Identifiants de crops dupliqués")
    groups: dict[str, set[str]] = defaultdict(set)
    selected = []
    counts: Counter[str] = Counter()
    for record in records:
        if record.frame.split is None:
            raise ManifestError("Séparer les vidéos avant de préparer les crops")
        groups[record.frame.group_id].add(record.frame.split)
        groups[f"video:{record.frame.video_id}"].add(record.frame.split)
        groups[f"image:{record.image_key}"].add(record.frame.split)
    if any(len(splits) > 1 for splits in groups.values()):
        raise ManifestError("Fuite de groupe vidéo entre ensembles")
    for record in sorted(
        records, key=lambda r: (r.review != "accept", -r.detection_confidence, r.crop_id)
    ):
        if record.review != "accept":
            if (
                not allow_filename_labels
                or record.review != "pending"
                or record.frame.species_candidate not in classes.names
            ):
                continue
            # L'état reste pending : un label de nom de fichier n'est pas une revue humaine.
            record = record.model_copy(update={"label": record.frame.species_candidate})
        if record.label not in classes.names:
            raise ManifestError("Label humain absent ou inconnu")
        if counts[record.frame.video_id] < max_per_video:
            selected.append(record)
            counts[record.frame.video_id] += 1
    return tuple(selected)


class CropsDataset:
    """Dataset compatible DataLoader sans importer PyTorch à la définition."""

    def __init__(
        self,
        records: Sequence[CropRecord],
        storage: Storage,
        classes: ClassManifest,
        transform: Any,
        *,
        allow_filename_labels: bool = False,
    ) -> None:
        self.records, self.storage, self.classes, self.transform = (
            records,
            storage,
            classes,
            transform,
        )
        self.allow_filename_labels = allow_filename_labels

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        record = self.records[index]
        provisional = (
            self.allow_filename_labels
            and record.review == "pending"
            and record.label == record.frame.species_candidate
        )
        if (
            record.review != "accept" and not provisional
        ) or record.label not in self.classes.names:
            raise ManifestError("Un dataset d'entraînement exige des crops validés")
        with Image.open(BytesIO(self.storage.read_bytes(record.image_key))) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, self.classes.names.index(record.label)
