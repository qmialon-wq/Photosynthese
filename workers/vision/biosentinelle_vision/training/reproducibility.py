import hashlib
import json
import platform
import random
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from ..classes import ClassManifest
from ..config import VisionSettings
from ..datasets.inventory import file_hash
from ..schemas import CropRecord
from ..storage import LocalStorage


def identity(
    records: Sequence[CropRecord],
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
) -> str:
    config = settings.training.model_dump(
        mode="json",
        exclude={
            "run_id",
            "resume_checkpoint",
            "database_metrics",
            "register_model_name",
            "activate_on_success",
        },
    )
    source = {
        "classes": classes.model_dump(mode="json"),
        "config": config,
        "seed": settings.seed,
        "video_truth_sha256": file_hash(settings.training.video_truth_manifest)
        if settings.training.video_truth_manifest is not None
        else None,
        "crops": settings.crops.model_dump(),
        "records": [
            {"record": r.model_dump(mode="json"), "sha256": file_hash(storage.path(r.image_key))}
            for r in sorted(records, key=lambda r: r.crop_id)
        ],
    }
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def versions() -> dict[str, str]:
    result = {"python": platform.python_version()}
    for name in ("torch", "torchvision", "timm", "numpy", "biosentinelle-vision"):
        try:
            result[name] = str(version(name))
        except PackageNotFoundError:
            result[name] = "not_installed"
    return result


def rng_state(generator: Any, capture_cuda: bool = False) -> dict[str, Any]:
    import numpy as np
    import torch

    numpy_state = np.random.get_state()
    return {
        "python": random.getstate(),
        "numpy": [
            numpy_state[0],
            numpy_state[1].tolist(),
            numpy_state[2],
            numpy_state[3],
            numpy_state[4],
        ],
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if capture_cuda else [],
        "sampler": generator.get_state(),
    }


def restore_rng(state: dict[str, Any], generator: Any) -> None:
    import numpy as np
    import torch

    random.setstate(state["python"])
    n = state["numpy"]
    np.random.set_state((n[0], np.asarray(n[1], dtype=np.uint32), n[2], n[3], n[4]))
    torch.set_rng_state(state["torch"])
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])
    generator.set_state(state["sampler"])
