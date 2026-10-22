import json
import os
import tempfile
from pathlib import Path


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        if Path(key).is_absolute():
            raise ValueError("Une clé de stockage doit être relative")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Clé hors de la racine de stockage")
        return path

    def read_bytes(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def write_bytes(self, key: str, value: bytes) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def write_json(self, key: str, value: object) -> None:
        self.write_bytes(
            key, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        )
