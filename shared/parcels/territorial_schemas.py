"""HTTP/worker contract: declarations, human observations and map evidence stay distinct."""

from typing import Any, Literal

from pydantic import Field, model_validator

from shared.documents.schemas import Body


class Location(Body):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    provenance: Literal["numeric", "map"] = "numeric"
    expected_revision: int = Field(ge=0)


class TerritorialRequest(Body):
    expected_location_revision: int = Field(gt=0)
    expected_profile_revision: int = Field(ge=0)


class Action(Body):
    category: Literal["avoid", "reduce", "investigate"]
    project_action: str
    issue: str
    action: str
    rationale: str
    evidence_refs: list[str]
    source_refs: list[str]
    preconditions: list[str]
    missing_information: list[str]
    limitations: list[str]
    evidence_status: Literal["general_verification", "conditional_proposal"]


class Compensation(Body):
    status: Literal["not_assessed"]


class Analysis(Body):
    rules_version: str
    analysis_revision: int
    facts: list[dict[str, Any]]
    project_concerns: list[dict[str, Any]]
    actions: list[Action]
    unknowns: list[str]
    limitations: list[str]
    sources: list[dict[str, Any]]
    compensation: Compensation
    documentary: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_action_evidence(self) -> "Analysis":
        fact_ids = {fact["id"] for fact in self.facts}
        source_ids = {source["id"] for source in self.sources}
        for action in self.actions:
            if set(action.evidence_refs) - fact_ids or set(action.source_refs) - source_ids:
                raise ValueError("Référence de preuve ou de source inconnue")
            if action.category in ("avoid", "reduce"):
                reviewed = any(
                    source["id"] in action.source_refs
                    and source.get("applicability") == "reviewed"
                    and source.get("quote")
                    for source in self.sources
                )
                if (
                    action.evidence_status != "conditional_proposal"
                    or not reviewed
                    or not action.preconditions
                ):
                    raise ValueError(
                        "Piste ERC conditionnelle et source applicable examinée requises"
                    )
        return self
