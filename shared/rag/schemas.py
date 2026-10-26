from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from shared.documents.schemas import Body, SpeciesKey
from shared.parcels.schemas import Profile


class Filters(Body):
    species: list[SpeciesKey] = Field(default_factory=list, max_length=10)
    habitat: str | None = Field(default=None, min_length=2, max_length=150)
    territory: str | None = Field(default=None, min_length=2, max_length=150)
    sources: list[str] = Field(default_factory=list, max_length=10)
    published_after: date | None = None
    published_before: date | None = None

    @model_validator(mode="after")
    def dates(self) -> "Filters":
        if self.published_after and self.published_before:
            if self.published_after > self.published_before:
                raise ValueError("Intervalle de publication inversé")
        return self


class Search(Body):
    question: str = Field(min_length=3, max_length=2000, pattern=r"\S")
    filters: Filters = Field(default_factory=Filters)
    mode: Literal["hybrid", "lexical"] = "hybrid"
    limit: int = Field(default=8, ge=1, le=30)
    rerank: bool = False


class Report(Search):
    video_ids: list[str] = Field(default_factory=list, max_length=100)
    profile: Profile | None = None


class Context(Body):
    observed_at: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    territory: str | None = Field(default=None, max_length=200)
    habitat: str | None = Field(default=None, max_length=200)
    provenance: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def coordinates(self) -> "Context":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude et longitude requises ensemble")
        if self.observed_at and self.observed_at.tzinfo is None:
            raise ValueError("Fuseau horaire requis")
        return self


class Taxonomy(Body):
    cd_nom: int = Field(gt=0)
    taxref_version: str = Field(min_length=1, max_length=100)
    scientific_name: str = Field(min_length=3, max_length=200)
    source_url: HttpUrl


class Index(Body):
    document_ids: list[UUID] = Field(default_factory=list, max_length=200)


class DocumentContext(Body):
    habitats: list[str] = Field(default_factory=list, max_length=20)
    territories: list[str] = Field(default_factory=list, max_length=20)
    provenance: str = Field(min_length=3, max_length=2000)


class EvaluationCase(Body):
    search: Search
    relevant_chunks: list[str] = Field(min_length=1, max_length=200)


class Evaluation(Body):
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)
