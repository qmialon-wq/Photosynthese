import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..errors import GpuBusyError


@contextmanager
def exclusive_gpu(device: str, path: Path) -> Iterator[None]:
    """Verrou interprocessus partagé, libéré par l'OS même après une interruption."""
    if device != "cuda":
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise GpuBusyError("Une opération GPU est déjà active") from exc
        else:
            import fcntl

            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise GpuBusyError("Une opération GPU est déjà active") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
