from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIOSENTINELLE_DOCUMENTS_", extra="ignore")
    root: Path = Path("/storage/documents")
    contact_email: str = ""
    openalex_api_key: SecretStr | None = None
    request_interval: float = Field(default=1.0, ge=0.2)
    timeout_seconds: float = Field(default=25, gt=0, le=120)
    retries: int = Field(default=3, ge=0, le=6)
    cache_ttl_seconds: int = Field(default=86400, ge=0)
    max_file_bytes: int = Field(default=32 * 1024 * 1024, ge=1024, le=128 * 1024 * 1024)
    max_pdf_pages: int = Field(default=1000, ge=1, le=5000)
    max_text_chars: int = Field(default=4000000, ge=1000)
    chunk_chars: int = Field(default=1600, ge=200, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
