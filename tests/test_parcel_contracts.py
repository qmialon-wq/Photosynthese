import pytest
from pydantic import ValidationError

from shared.parcels.report import THEMES, planning_questions, suggestions, supporting_sentence
from shared.parcels.schemas import Profile


def test_profile_is_small_typed_and_positive():
    body = Profile(area_m2=2500, land_type="pasture", project_type="housing")
    assert body.area_m2 == 2500 and body.expected_revision == 0
    for invalid in ({"area_m2": 0}, {"area_m2": float("nan")}, {"land_type": "invented"}):
        with pytest.raises(ValidationError):
            Profile(**{**body.model_dump(), **invalid})


def test_actions_require_explicit_support_and_reject_negation_or_caveat():
    theme = THEMES[0]
    assert supporting_sentence(
        theme, "We recommend preserving hedgerows in agricultural landscapes."
    )
    for text in (
        "Hedgerows occur in agricultural landscapes and foxes live nearby.",
        "We do not recommend preserving hedgerows in these study conditions.",
        "Preserving hedgerows should be avoided in the experimental enclosures.",
        "We recommend preserving hedgerows only if local conditions are suitable.",
    ):
        assert supporting_sentence(theme, text) is None


def test_no_sources_never_produces_sourced_recommendation():
    result = suggestions(THEMES[0], [], False)
    assert result["status"] == "insufficient_evidence"
    assert result["citation"] is None
    proposed = suggestions(
        THEMES[0],
        [
            {
                "citation": "S1",
                "text": "We recommend preserving hedgerows in agricultural landscapes.",
            }
        ],
        False,
    )
    assert proposed["citation"] == "S1" and proposed["species_conditional"] is True


def test_design_questions_change_with_land_and_activity():
    housing = planning_questions({"land_type": "woodland", "project_type": "housing"})
    livestock = planning_questions({"land_type": "pasture", "project_type": "livestock"})
    assert "habitation" in housing[0] and "forestiers" in housing[1]
    assert "clôtures" in livestock[0] and "prairies" in livestock[1]


def test_similar_words_do_not_support_unrelated_land_design():
    assert (
        supporting_sentence(THEMES[0], "We recommend preserving hedgehogs in agricultural areas.")
        is None
    )
    lighting = "We recommend reducing artificial lighting near wildlife habitats."
    assert supporting_sentence(THEMES[2], lighting)
    assert supporting_sentence(THEMES[3], lighting) is None
