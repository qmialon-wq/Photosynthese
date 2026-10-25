import re
from typing import Any, Literal
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceName = Literal["openalex", "crossref", "europepmc"]
SpeciesKey = Literal[
    "chevreuil",
    "sanglier",
    "buse",
    "pigeons",
    "martres",
    "renards",
    "blaireaux",
    "chouette",
    "geai",
    "faisans",
]


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = unquote(value.strip()).lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    if not re.fullmatch(r"10\.\d{4,9}/\S+", value):
        raise ValueError("DOI invalide")
    return value


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Search(Body):
    species: list[str] = Field(default_factory=list, max_length=10)
    habitats: list[str] = Field(default_factory=list, max_length=10)
    territories: list[str] = Field(default_factory=list, max_length=10)
    topics: list[str] = Field(default_factory=list, max_length=10)
    sources: list[SourceName] = Field(default=["openalex", "crossref", "europepmc"], min_length=1)
    limit_per_source: int = Field(default=20, ge=1, le=100)
    max_pages: int = Field(default=1, ge=1, le=10)
    download_fulltext: bool = False
    focus: Literal["general", "human_activities"] = "general"
    activity: Literal[
        "all", "lighting", "transport", "agriculture", "urban", "recreation", "forestry", "noise"
    ] = "all"

    @field_validator("species", "habitats", "territories", "topics")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        if any(not v.strip() or len(v) > 200 or any(ord(c) < 32 for c in v) for v in values):
            raise ValueError("Termes non vides de 200 caractères maximum requis")
        return list(dict.fromkeys(v.strip() for v in values))

    @model_validator(mode="after")
    def not_empty(self) -> "Search":
        if not any((self.species, self.habitats, self.territories, self.topics)):
            raise ValueError("Fournir au moins une espèce, un habitat, un territoire ou un thème")
        self.sources = list(dict.fromkeys(self.sources))
        return self


class Watch(Body):
    name: str = Field(min_length=1, max_length=150)
    search: Search
    interval_seconds: int = Field(default=86400, ge=60, le=31536000)
    enabled: bool = False


class ManualImport(Body):
    path: str = Field(min_length=1, max_length=500)
    title: str | None = Field(default=None, max_length=1000)
    doi: str | None = None
    license: str | None = Field(default=None, max_length=500)
    rights_confirmed: bool
    species: list[SpeciesKey] = Field(default_factory=list, max_length=10)

    _doi = field_validator("doi")(normalize_doi)

    @field_validator("path")
    @classmethod
    def relative(cls, value: str) -> str:
        from pathlib import PurePosixPath, PureWindowsPath

        if (
            "\\" in value
            or "\x00" in value
            or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).drive
            or ".." in PurePosixPath(value).parts
        ):
            raise ValueError("Chemin relatif à documents/inbox requis")
        if PurePosixPath(value).suffix.lower() not in (".pdf", ".txt", ".md"):
            raise ValueError("Document PDF, TXT ou Markdown requis")
        return value

    @model_validator(mode="after")
    def permission(self) -> "ManualImport":
        if not self.rights_confirmed:
            raise ValueError("Confirmer le droit de conserver et traiter ce document localement")
        return self


class Decision(Body):
    relevance: Literal["pending", "accepted", "rejected"]
    quality: Literal["pending", "accepted", "rejected"]
    note: str = Field(default="", max_length=4000)


class Selection(Body):
    enabled: bool


class Collect(Body):
    species: list[SpeciesKey] = Field(default_factory=list, max_length=10)


class RemoveDocuments(Body):
    species: SpeciesKey
    documents: list[str] = Field(min_length=1, max_length=200)

    @field_validator("documents")
    @classmethod
    def identifiers(cls, values: list[str]) -> list[str]:
        from uuid import UUID

        return list(dict.fromkeys(str(UUID(value)) for value in values))


class FullText(Body):
    url: str
    license: str
    evidence: str
    format: Literal["pdf", "xml"] = "pdf"


class Publication(Body):
    source: SourceName | Literal["manual"]
    source_id: str
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    published_date: str | None = None
    abstract: str | None = None
    url: str | None = None
    license: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    fulltexts: list[FullText] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    _doi = field_validator("doi")(normalize_doi)
