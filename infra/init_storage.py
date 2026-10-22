"""Prépare uniquement les répertoires gérés, sans parcourir les données utilisateur."""

import os
from pathlib import Path

for name in (
    "datasets",
    "datasets/inbox",
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
    # Boîte de dépôt locale : écriture depuis le compte hôte, sources montées en lecture seule.
    path.chmod(0o1777 if name == "datasets/inbox" else 0o775)
