"""Prépare uniquement les répertoires gérés, sans parcourir les données utilisateur."""

import os
from pathlib import Path

for name in (
    "datasets",
    "models",
    "models/cache",
    "models/cache/torch",
    "models/cache/huggingface",
    "checkpoints",
    "documents",
    "results",
):
    path = Path("/storage") / name
    path.mkdir(parents=True, exist_ok=True)
    os.chown(path, 10001, 10001)
    path.chmod(0o775)
