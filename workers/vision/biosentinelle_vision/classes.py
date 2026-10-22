from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from .errors import ManifestError


class Species(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: int
    name: str
    latin: str
    aliases: tuple[str, ...]


class ClassManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str
    classes: tuple[Species, ...]

    @model_validator(mode="after")
    def ordered_unique_classes(self) -> "ClassManifest":
        if not self.classes or [s.id for s in self.classes] != list(range(len(self.classes))):
            raise ValueError("Les indices doivent être contigus et ordonnés à partir de zéro")
        if len(set(self.names)) != len(self.classes):
            raise ValueError("Classes dupliquées")
        return self

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(species.name for species in self.classes)

    def check_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        if tuple(checkpoint.get("classes", ())) != self.names:
            raise ManifestError(
                "Ordre/classes du checkpoint incompatible ; aucune conversion implicite"
            )
        version = checkpoint.get("class_manifest_version")
        if version is not None and version != self.version:
            raise ManifestError("Version du manifeste du checkpoint incompatible")


def load_classes(path: Path | None = None) -> ClassManifest:
    source = (
        path if path is not None else files(__package__).joinpath("manifests/classes-v3-10.json")
    )
    return ClassManifest.model_validate_json(source.read_text(encoding="utf-8"))
