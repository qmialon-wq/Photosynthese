from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIOSENTINELLE_RAG_", extra="ignore")
    model_root: Path = Path("/storage/models/rag")
    # Optional local manifest for another compatible ONNX encoder; never remote Python code.
    model_manifest: Path | None = None
    min_similarity: float = Field(default=0.80, ge=0, le=1)
    threads: int = Field(default=2, ge=1, le=8)

    @field_validator("model_manifest", mode="before")
    @classmethod
    def empty_manifest(cls, value: object) -> object:
        return None if value == "" else value
