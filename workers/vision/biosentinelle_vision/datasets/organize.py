"""Classement matériel depuis les noms : copies, traçabilité et labels candidats."""

import csv
import io
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from ..classes import ClassManifest
from ..config import SplitConfig
from ..errors import ManifestError
from ..schemas import Inventory
from ..storage import LocalStorage
from .inventory import file_hash, inventory
from .split import split_videos


def organize_videos(
    source: Path,
    destination: Path,
    reports: LocalStorage,
    classes: ClassManifest,
    split_config: SplitConfig,
    seed: int = 42,
) -> dict[str, Any]:
    source, destination = source.resolve(), destination.resolve()
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ManifestError("Les dossiers source et classé doivent être distincts et non imbriqués")
    original = inventory(source, classes)
    destination.mkdir(parents=True, exist_ok=True)
    for name in (*classes.names, "_a_verifier"):
        (destination / name).mkdir(exist_ok=True)
    records, rows, issues = [], [], []
    copied = unchanged = 0
    for video in original.videos:
        species = video.species_candidate
        folder = species if species is not None and video.error is None else "_a_verifier"
        relative = Path(folder) / video.relative_path
        target = (destination / relative).resolve()
        try:
            if not target.is_relative_to(destination):
                raise ManifestError("Chemin de destination hors du dossier classé")
            if video.content_hash is None:
                raise ManifestError("Vidéo source inaccessible, empreinte indisponible")
            if target.exists():
                if not target.is_file() or file_hash(target) != video.content_hash:
                    raise ManifestError("Destination différente déjà présente ; aucun écrasement")
                unchanged += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".copy-", dir=target.parent)
                os.close(fd)
                try:
                    shutil.copyfile(source / video.relative_path, temporary)
                    if file_hash(Path(temporary)) != video.content_hash:
                        raise ManifestError("Contenu modifié pendant la copie")
                    if target.exists():
                        if file_hash(target) != video.content_hash:
                            raise ManifestError("Destination modifiée pendant la copie")
                        unchanged += 1
                    else:
                        os.replace(temporary, target)
                        target.chmod(0o644)
                        copied += 1
                finally:
                    Path(temporary).unlink(missing_ok=True)
            records.append(video.model_copy(update={"relative_path": relative.as_posix()}))
            rows.append(
                {
                    "source": video.relative_path,
                    "destination": relative.as_posix(),
                    "species_candidate": species or "",
                    "label_source": "filename",
                    "human_validated": False,
                    "sha256": video.content_hash,
                    "reading_error": video.error or "",
                }
            )
        except (OSError, ManifestError) as exc:
            issues.append({"source": video.relative_path, "error": str(exc)})
    classified = Inventory(
        dataset_root=str(destination),
        class_manifest_version=classes.version,
        videos=tuple(records),
    )
    split_error = None
    try:
        classified = split_videos(classified, split_config, seed)
    except ManifestError as exc:
        split_error = str(exc)
    reports.write_json("videos.json", classified.model_dump(mode="json"))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "source",
            "destination",
            "species_candidate",
            "label_source",
            "human_validated",
            "sha256",
            "reading_error",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    reports.write_bytes("classement.csv", buffer.getvalue().encode("utf-8-sig"))
    counts = Counter(Path(v.relative_path).parts[0] for v in records)
    result = {
        "source": str(source),
        "destination": str(destination),
        "total": len(records),
        "copied": copied,
        "unchanged": unchanged,
        "counts": dict(sorted(counts.items())),
        "issues": issues,
        "split_error": split_error,
        "label_source": "filename",
        "human_validated": False,
        "note": "Classement vidéo provisoire ; aucune validation d'espèce par animal ou crop",
    }
    reports.write_json("classification.json", result)
    return result
