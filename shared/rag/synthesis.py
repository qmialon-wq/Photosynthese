"""Typed evidence notes and four-page planning reports; no model dependency."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Finding(Strict):
    chunk_id: str = ""
    quote_id: str = ""
    quote_index: int = Field(default=0, ge=0)
    quote: str = Field(default="", max_length=900, json_schema_extra={"const": ""})
    finding: str = Field(default="", max_length=1000, json_schema_extra={"const": ""})
    limits: str = Field(default="", max_length=1200, json_schema_extra={"const": ""})
    role: Literal["result", "limitation", "recommendation", "context"] = "context"
    direction: Literal["benefit", "harm", "mixed", "uncertain"]


class Notes(Strict):
    findings: list[Finding] = Field(max_length=3)
    relevance: str = Field(
        min_length=3,
        max_length=1000,
        json_schema_extra={"enum": ["relevant", "not_relevant"]},
    )


class Paragraph(Strict):
    text: str = Field(min_length=20, max_length=2600)
    citations: list[str] = Field(min_length=1, max_length=6)


class Action(Strict):
    action_type: Literal["territorial", "assessment"] = "territorial"
    title: str = Field(min_length=5, max_length=180)
    action: str = Field(min_length=30, max_length=500)
    location: str = Field(min_length=5, max_length=250)
    rationale: str = Field(min_length=15, max_length=400)
    conditions: str = Field(min_length=10, max_length=450)
    priority: Literal["before_project", "design", "works", "monitoring"]
    monitoring: str = Field(min_length=10, max_length=300)
    citations: list[str] = Field(min_length=1, max_length=12)


class Page(Strict):
    title: str = Field(min_length=5, max_length=180)
    paragraphs: list[Paragraph] = Field(min_length=3, max_length=5)


class Actions(Strict):
    actions: list[Action] = Field(max_length=6)
