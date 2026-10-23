"""Clés locales confinées, écriture atomique et empreintes de contenu."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


class DocumentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if Path(key).is_absolute() or not target.is_relative_to(self.root):
            raise ValueError("Clé documentaire hors stockage")
        return target

    def write(self, key: str, data: bytes) -> Path:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".document-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return path

    def json(self, key: str, data: object) -> Path:
        return self.write(key, json.dumps(data, ensure_ascii=False, allow_nan=False).encode())

    def content(self, data: bytes, extension: str) -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        key = f"assets/{digest[:2]}/{digest}.{extension}"
        target = self.path(key)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Fichier documentaire existant corrompu")
        if not target.exists():
            self.write(key, data)
        return digest, key
