from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIOSENTINELLE_RAG_", extra="ignore")
    model_root: Path = Path("/storage/models/rag")
    # Optional local manifest for another compatible ONNX encoder; never remote Python code.
    model_manifest: Path | None = None
    min_similarity: float = Field(default=0.80, ge=0, le=1)
    threads: int = Field(default=2, ge=1, le=8)
    generation_enabled: bool = False
    generator_url: str = "http://ollama:11434"
    generator_model: str = "qwen3:4b-instruct-2507-q4_K_M"
    generator_timeout: int = Field(default=600, ge=10, le=3600)
    generation_device: Literal["cpu", "cuda"] = "cpu"
    reading_mode: Literal["balanced", "exhaustive"] = "balanced"

    @field_validator("model_manifest", mode="before")
    @classmethod
    def empty_manifest(cls, value: object) -> object:
        return None if value == "" else value
