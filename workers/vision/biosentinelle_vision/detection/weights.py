"""Registre explicite des poids testés ; aucun accès réseau à l'import."""

import hashlib
import os
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..errors import ModelError
from ..storage import LocalStorage

MODEL_ID = "md_v5a.0.0"
PACKAGE_VERSION = "10.0.28"
MODEL_URL = "https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt"
# MD5 publié dans run_detector. SHA256 calculé sur l'artefact officiel vérifié MD5.
MODEL_MD5 = "ec1d7603ec8cf642d6e0cd008ba2be8c"
MODEL_SHA256 = "94e88fe97c8050f2e3d0cc4cb4f64729d639d74312dcbe2f74f8eecd3b01b276"


def verify_weights(path: Path) -> str:
    if not path.is_file() or path.suffix.lower() != ".pt":
        raise ModelError(f"Poids {MODEL_ID} manquants : {path}. Exécuter make detector-fetch.")
    sha, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            sha.update(chunk)
            md5.update(chunk)
    if sha.hexdigest() != MODEL_SHA256 or md5.hexdigest() != MODEL_MD5:
        raise ModelError(
            f"Poids incompatibles ou corrompus : {path}. Seul {MODEL_ID} est enregistré ; "
            "aucun chargement YOLO arbitraire. Déplacer ce fichier avant de le retélécharger."
        )
    return sha.hexdigest()


def fetch_weights(path: Path) -> dict[str, str | bool]:
    """Téléchargement uniquement sur appel explicite ; cache contrôlé à chaque appel."""
    path = path.resolve()
    cached = path.exists()
    if not cached:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".pt", dir=path.parent)
        try:
            request = Request(MODEL_URL, headers={"User-Agent": "BioSentinelle/0.1"})
            with os.fdopen(fd, "wb") as output, urlopen(request, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            verify_weights(Path(temporary))
            os.replace(temporary, path)
        except (OSError, URLError) as exc:
            raise ModelError(f"Téléchargement {MODEL_ID} vers {path} impossible : {exc}") from exc
        finally:
            Path(temporary).unlink(missing_ok=True)
    digest = verify_weights(path)
    metadata: dict[str, str | bool] = {
        "model_id": MODEL_ID,
        "package_version": PACKAGE_VERSION,
        "url": MODEL_URL,
        "sha256": digest,
        "path": str(path),
        "cached": cached,
    }
    LocalStorage(path.parent).write_json(f"{path.name}.manifest.json", metadata)
    return metadata
