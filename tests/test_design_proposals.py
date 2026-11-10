"""Project design alternatives, separate from ecological recommendations."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from shared.parcels.territorial_rules import analyze
from shared.parcels.territorial_schemas import Analysis
from tests.test_territorial_rules import inputs, layers

CODES = ["fencing", "outdoor_lighting", "vegetation_removal", "earthworks", "soil_sealing"]


def validate(codes, state="empty", observations=False, documents=None):
    result = analyze(inputs(codes, observations), layers(state), 1, documents)
    Analysis.model_validate(result)
    return result


@pytest.mark.parametrize("code", CODES)
def test_each_declared_intervention_has_concrete_conditional_options(code):
    result = validate([code])
    (project,) = result["design_proposals"]
    assert project["project_action"] == code
    assert project["initial_intervention"] and project["issue"]
    assert len(project["alternatives"]) >= 2
    for option in project["alternatives"]:
        assert option["category"] in ("avoid", "reduce")
        assert option["proposal"].startswith("Si ")
        assert option["project_change"] and option["conditions"] and option["limitations"]
        assert option["status"] == "conditional_design_option"
        assert option["evidence_refs"] == [f"project:{code}"]
        assert option["source_refs"] and option["justification"]["level"] == "exploratory"
    assert result["compensation"] == {"status": "not_assessed"}
    assert all(a["category"] == "investigate" for a in result["actions"])


def test_a_b_and_switch_change_only_design_options_for_declared_interventions():
    a = validate(["outdoor_lighting"], "success", True)
    b = validate(["outdoor_lighting", "fencing"], "success", True)
    c = validate(["earthworks"], "success", True)
    assert b["design_proposals"][0] == a["design_proposals"][0]
    assert {p["project_action"] for p in b["design_proposals"]} == {"fencing", "outdoor_lighting"}
    assert [p["project_action"] for p in c["design_proposals"]] == ["earthworks"]
    assert {o["id"] for p in c["design_proposals"] for o in p["alternatives"]}.isdisjoint(
        {o["id"] for p in b["design_proposals"] for o in p["alternatives"]}
    )


def test_empty_missing_interventions_never_invent_a_project():
    for profile in ({}, {"interventions": []}):
        result = analyze({"profile": profile, "observations": []}, layers("success"), 1)
        assert result["design_proposals"] == []
    old = validate(["fencing"])
    del old["design_proposals"]
    assert Analysis.model_validate(old).design_proposals == []


@pytest.mark.parametrize("state", ["empty", "unavailable", "error"])
def test_no_ign_result_keeps_options_exploratory_without_negative_conclusions(state):
    result = validate(CODES, state)
    options = [o for p in result["design_proposals"] for o in p["alternatives"]]
    assert len(options) == 12
    assert all(o["justification"]["level"] == "exploratory" for o in options)
    assert all(not any(ref.startswith("ign:") for ref in o["evidence_refs"]) for o in options)
    assert all(o["limitations"] for o in options)


def test_contextualization_uses_relevant_verified_records_only():
    fence = validate(["fencing"], "success", True)["design_proposals"][0]["alternatives"][0]
    assert fence["justification"]["level"] == "contextualized"
    assert fence["evidence_refs"] == ["project:fencing", "human:s1:2"]
    assert not any(ref.startswith("ign:") for ref in fence["evidence_refs"])
    soil = validate(["soil_sealing"], "success")["design_proposals"][0]["alternatives"][0]
    assert soil["justification"]["level"] == "exploratory"
    assert soil["evidence_refs"] == ["project:soil_sealing"]
    lighting = validate(["outdoor_lighting"], "success", True)["design_proposals"][0][
        "alternatives"
    ][0]
    assert lighting["justification"]["level"] == "exploratory"
    predicted = inputs(["fencing"], False)
    predicted["observations"] = [
        {"sample_id": "prediction", "revision": 1, "species": "blaireaux", "state": "pending"}
    ]
    result = analyze(predicted, layers("success"), 1)
    assert (
        result["design_proposals"][0]["alternatives"][0]["justification"]["level"] == "exploratory"
    )
    assert result["design_proposals"][0]["alternatives"][0]["evidence_refs"] == ["project:fencing"]
    bird = inputs(["fencing"])
    bird["observations"][0]["species"] = "buse"
    assert (
        analyze(bird, layers("success"), 1)["design_proposals"][0]["alternatives"][0][
            "justification"
        ]["level"]
        == "exploratory"
    )


def reviewed_source():
    return {
        "id": "doc:fixture",
        "title": "Synthetic reviewed source, not real science",
        "applicability": "reviewed",
        "evidence_type": "scientific",
        "project_action": "outdoor_lighting",
        "category": "reduce",
        "design_alternative_ids": ["outdoor_lighting:shorter_operation"],
        "quote": "Synthetic source quote explicitly supporting this option.",
        "proposal": "comparer une durée de fonctionnement réduite",
        "sha256": "a" * 64,
        "page": 3,
        "species": ["blaireaux"],
    }


def test_scientific_level_is_specific_to_reviewed_alternative_and_species():
    doc = reviewed_source()
    result = validate(["outdoor_lighting"], "success", True, [doc])
    options = result["design_proposals"][0]["alternatives"]
    qualified = [o for o in options if o["justification"]["level"] == "scientifically_qualified"]
    assert [o["id"] for o in qualified] == ["outdoor_lighting:shorter_operation"]
    assert qualified[0]["status"] == "conditional_design_option"
    assert "doc:fixture" in qualified[0]["source_refs"]
    assert "human:s1:2" in qualified[0]["evidence_refs"]
    for field, value in [
        ("applicability", "not_assessed"),
        ("design_alternative_ids", []),
        ("evidence_type", "general_guide"),
        ("page", None),
        ("quote", ""),
        ("sha256", None),
        ("species", ["chouette"]),
        ("category", "avoid"),
    ]:
        invalid = {**doc, field: value}
        changed = validate(["outdoor_lighting"], "success", True, [invalid])
        assert all(
            o["justification"]["level"] != "scientifically_qualified"
            for o in changed["design_proposals"][0]["alternatives"]
        )


def test_lexical_document_is_visible_without_promoting_an_option():
    doc = {**reviewed_source(), "applicability": "not_assessed", "relevance_reason": "lexical only"}
    result = validate(["outdoor_lighting"], "empty", False, [doc])
    assert all(
        o["justification"]["level"] == "exploratory"
        for o in result["design_proposals"][0]["alternatives"]
    )
    assert "doc:fixture" in result["design_proposals"][0]["alternatives"][0]["source_refs"]


def test_contract_rejects_unknown_refs_or_unjustified_levels():
    original = validate(["fencing"])
    for field, value in [
        ("source_refs", ["invented"]),
        ("id", "outdoor_lighting:unrelated"),
        ("evidence_refs", ["invented"]),
        ("justification", {"level": "contextualized", "reason": "invalid"}),
        ("justification", {"level": "scientifically_qualified", "reason": "invalid"}),
        ("category", "compensate"),
        ("status", "validated"),
    ]:
        result = deepcopy(original)
        result["design_proposals"][0]["alternatives"][0][field] = value
        with pytest.raises(ValidationError):
            Analysis.model_validate(result)
    original["design_proposals"].append(deepcopy(original["design_proposals"][0]))
    with pytest.raises(ValidationError, match="dupliquée"):
        Analysis.model_validate(original)


def test_context_requires_the_sources_of_its_cited_facts():
    result = validate(["fencing"], "success", True)
    result["design_proposals"][0]["alternatives"][0]["source_refs"] = ["erc-framework"]
    with pytest.raises(ValidationError, match="explicitement citées"):
        Analysis.model_validate(result)
