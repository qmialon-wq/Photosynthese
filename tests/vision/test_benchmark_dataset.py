import json

import numpy as np
import pytest
from biosentinelle_vision.datasets.benchmark import prepare_dataset
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.schemas import Inventory, VideoRecord
from biosentinelle_vision.storage import LocalStorage
from PIL import Image

from .test_make_commands import reviewed_dataset


def test_benchmark_is_reproducible_uses_human_labels_and_warns_sparse(tmp_path, classes):
    _, source = reviewed_dataset(tmp_path, classes)
    for index, crop in enumerate(source.crops):
        Image.fromarray(
            np.random.default_rng(index).integers(0, 255, (48, 48, 3), dtype=np.uint8)
        ).save(tmp_path / crop.image_key)
    inventory = Inventory(
        class_manifest_version=classes.version,
        dataset_root="unused",
        videos=tuple(
            VideoRecord(
                video_id=c.frame.video_id,
                relative_path=c.crop_id + ".mp4",
                content_hash=c.crop_id,
                group_id="sequence-" + c.frame.video_id,
                split=c.frame.split,
            )
            for c in source.crops
        ),
    )
    destination = LocalStorage(tmp_path / "versions")
    a = prepare_dataset(source, inventory, LocalStorage(tmp_path), destination, classes)
    b = prepare_dataset(source, inventory, LocalStorage(tmp_path), destination, classes)
    assert a == b and a["samples"] == 20 and a["warnings"]
    rows = json.loads(destination.read_bytes(a["dataset_version"] + "/manifest.json"))["samples"]
    assert all(r["label_source"] == "human" and len(r["image_sha256"]) == 64 for r in rows)
    assert rows[0]["source_video"].endswith(".mp4")
    assert rows[0]["group_id"].startswith("sequence-")
    assert rows[0]["foreground_fraction_method"] == "geometric_prior_not_measured"
    crossed = list(inventory.videos)
    crossed[10] = crossed[10].model_copy(update={"group_id": crossed[0].group_id})
    with pytest.raises(ManifestError, match="entre splits"):
        prepare_dataset(
            source,
            inventory.model_copy(update={"videos": tuple(crossed)}),
            LocalStorage(tmp_path),
            destination,
            classes,
        )
    # Une copie inter-split ne peut entrer dans un benchmark.
    (tmp_path / source.crops[10].image_key).write_bytes(
        (tmp_path / source.crops[0].image_key).read_bytes()
    )
    with pytest.raises(ManifestError, match="entre splits"):
        prepare_dataset(source, inventory, LocalStorage(tmp_path), destination, classes)
