"""Description légère du corpus local préparé, sans dépendance ML."""

import json
from pathlib import Path
from typing import Any

BASE_DATASET_ID = "base"


def describe_base_dataset(results: Path) -> dict[str, Any]:
    description: dict[str, Any] = {
        "id": BASE_DATASET_ID,
        "name": "Corpus de base",
        "source": "base",
        "video_count": None,
        "crop_count": None,
        "ready": False,
        "warning": "Labels provisoires issus des noms ; les corrections humaines priment.",
    }
    try:
        inventory = json.loads((results / "classification/videos.json").read_text(encoding="utf-8"))
        manifest = json.loads((results / "training.json").read_text(encoding="utf-8"))
        if inventory["class_manifest_version"] != manifest["class_manifest_version"]:
            raise ValueError("Versions des classes incompatibles")
        videos, crops = inventory["videos"], manifest["crops"]
        if not isinstance(videos, list) or not isinstance(crops, list) or not videos or not crops:
            raise ValueError("Corpus ou recadrages vides")
        description.update(video_count=len(videos), crop_count=len(crops), ready=True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        description["unavailable_reason"] = (
            "Corpus non préparé ou illisible. Exécuter make prepare-training DEVICE=cuda."
        )
        description["ready"] = False
        if not isinstance(exc, OSError):
            description["unavailable_reason"] = (
                "Manifestes du corpus invalides ; refaire la préparation."
            )
    return description
