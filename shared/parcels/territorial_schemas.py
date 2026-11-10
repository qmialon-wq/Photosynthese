"""HTTP/worker contract: declarations, human observations and map evidence stay distinct."""

from typing import Any, Literal

from pydantic import Field, model_validator

from shared.documents.schemas import Body
from shared.parcels.schemas import Intervention


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


class DesignJustification(Body):
    level: Literal["exploratory", "contextualized", "scientifically_qualified"]
    reason: str = Field(min_length=1)


class DesignAlternative(Body):
    id: str = Field(min_length=1)
    category: Literal["avoid", "reduce"]
    title: str = Field(min_length=1)
    proposal: str = Field(min_length=1)
    project_change: str = Field(min_length=1)
    conditions: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    source_refs: list[str]
    justification: DesignJustification
    status: Literal["conditional_design_option"]
    limitations: list[str] = Field(min_length=1)


class DesignProposal(Body):
    project_action: Intervention
    initial_intervention: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    alternatives: list[DesignAlternative] = Field(min_length=1)


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
    design_proposals: list[DesignProposal] = Field(default_factory=list)

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
        from shared.parcels.design import contextual_fact_ids, qualified_for

        by_source = {source["id"]: source for source in self.sources}
        seen_codes, seen_ids = set(), set()
        for proposal in self.design_proposals:
            code = proposal.project_action
            if code in seen_codes:
                raise ValueError("Intervention de conception dupliquée")
            seen_codes.add(code)
            for option in proposal.alternatives:
                if option.id in seen_ids:
                    raise ValueError("Alternative de conception dupliquée")
                seen_ids.add(option.id)
                if (
                    set(option.evidence_refs) - fact_ids
                    or set(option.source_refs) - source_ids
                    or f"project:{code}" not in option.evidence_refs
                    or not option.id.startswith(f"{code}:")
                    or not any(
                        f["id"] == f"project:{code}" and f["kind"] == "user_declaration"
                        for f in self.facts
                    )
                ):
                    raise ValueError("Déclaration et références de conception valides requises")
                cited_facts = [f for f in self.facts if f["id"] in option.evidence_refs]
                if any(set(f["source_refs"]) - set(option.source_refs) for f in cited_facts):
                    raise ValueError(
                        "Sources des faits de conception explicitement citées requises"
                    )
                level = option.justification.level
                if level == "contextualized" and not contextual_fact_ids(
                    code, cited_facts, [by_source[ref] for ref in option.source_refs]
                ):
                    raise ValueError("Contexte vérifié pertinent requis pour cette alternative")
                if level == "scientifically_qualified":
                    human_sources = {
                        ref
                        for f in cited_facts
                        if f["kind"] == "human_observation"
                        for ref in f["source_refs"]
                    }
                    observed = {
                        by_source[ref]["species"]
                        for ref in human_sources
                        if ref in by_source and by_source[ref].get("species")
                    }
                    if not any(
                        qualified_for(by_source[ref], code, option.id, option.category, observed)
                        for ref in option.source_refs
                    ):
                        raise ValueError(
                            "Source scientifique examinée pour l’alternative précise requise"
                        )
        return self
