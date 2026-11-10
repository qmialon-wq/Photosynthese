import pytest
from pydantic import ValidationError

from shared.parcels.schemas import Profile, ProfileDraft
from shared.parcels.territorial_schemas import Location

PROFILE = {"area_m2": 1000, "land_type": "pasture", "project_type": "housing"}


def test_draft_can_be_saved_but_cannot_generate_a_scientific_dossier():
    draft = ProfileDraft(area_m2=None, land_type="", project_type="", interventions=["fencing"])
    data = draft.persisted()
    assert data["area_m2"] is None and data["interventions"] == ["fencing"]
    with pytest.raises(ValidationError):
        Profile.model_validate(data)
    assert Profile.model_validate({**data, **PROFILE}).area_m2 == 1000


def test_interventions_missing_empty_and_preserved():
    old = Profile(**PROFILE)
    assert "interventions" not in old.persisted()
    previous = {**PROFILE, "interventions": ["fencing"]}
    assert old.persisted(previous)["interventions"] == ["fencing"]
    assert Profile(**PROFILE, interventions=[]).persisted(previous)["interventions"] == []
    assert Profile(**PROFILE, interventions=["fencing", "fencing"]).interventions == ["fencing"]
    with pytest.raises(ValidationError):
        Profile(**PROFILE, interventions=["other"])
    with pytest.raises(ValidationError):
        Profile(**PROFILE, interventions=None)


@pytest.mark.parametrize(
    "data",
    [
        {"latitude": 91, "longitude": 0},
        {"latitude": 0, "longitude": -181},
        {"latitude": float("nan"), "longitude": 0},
        {"latitude": 0, "longitude": float("inf")},
    ],
)
def test_invalid_point(data):
    with pytest.raises(ValidationError):
        Location(**data, expected_revision=0)
