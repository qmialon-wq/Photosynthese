from copy import deepcopy

from shared.parcels.territorial_rules import analyze


def inputs(codes=None, observations=True):
    return {
        "profile": {"interventions": codes or []},
        "observations": [
            {"sample_id": "s1", "revision": 2, "species": "blaireaux", "state": "validated"}
        ]
        if observations
        else [],
    }


def layers(state="success"):
    return {
        key: {
            "status": state,
            "source_url": "https://apicarto.ign.fr/api/nature/" + key,
            "retrieved_at": "2026-11-10T12:00:00Z",
            "features": [{"name": "Fixture de test", "source_id": "test-zone"}]
            if state == "success"
            else [],
        }
        for key in ("znieff1", "znieff2", "natura-habitat", "natura-oiseaux")
    }


def test_ab_only_fencing_concerns_change_same_point_same_observations():
    a = analyze(inputs(["outdoor_lighting"]), layers(), 1)
    b = analyze(inputs(["outdoor_lighting", "fencing"]), layers(), 2)
    assert [x for x in a["facts"] if x["kind"] != "user_declaration"] == [
        x for x in b["facts"] if x["kind"] != "user_declaration"
    ]
    assert [x for x in a["actions"] if x["project_action"] == "outdoor_lighting"] == [
        x for x in b["actions"] if x["project_action"] == "outdoor_lighting"
    ]
    action = next(x for x in b["actions"] if x["project_action"] == "fencing")
    assert action["evidence_refs"] == ["project:fencing", "human:s1:2"]
    assert action["category"] == "investigate" and action["missing_information"]
    assert len(b["actions"]) == len(a["actions"]) + 1


def test_c_d_empty_and_unavailable_never_mean_absence():
    c = analyze(inputs(["soil_sealing"]), layers("empty"), 1)
    d = analyze(inputs(["soil_sealing"]), layers("unavailable"), 1)
    assert len([f for f in c["facts"] if f["kind"] == "map_result"]) == 4
    assert "Aucun zonage renvoyé" in c["facts"][-1]["text"]
    assert len(d["unknowns"]) == 4
    assert all(f["kind"] != "map_result" for f in d["facts"])
    assert "absence" in " ".join(c["limitations"])
    assert all(a["category"] == "investigate" for a in c["actions"] + d["actions"])


def test_e_no_valid_species_and_predictions_excluded():
    data = inputs(["fencing"], observations=False)
    data["observations"] = [
        {"sample_id": "prediction", "revision": 1, "species": "blaireaux", "state": "predicted"}
    ]
    result = analyze(data, layers(), 1)
    assert not any(f["kind"] == "human_observation" for f in result["facts"])
    assert result["actions"][0]["evidence_refs"] == ["project:fencing"]
    assert result["unknowns"] and all(a["category"] == "investigate" for a in result["actions"])


def test_f_earthworks_intersection_only_triggers_examination():
    result = analyze(inputs(["earthworks"]), layers(), 1)
    assert result["actions"][0]["category"] == "investigate"
    assert len(result["actions"][0]["evidence_refs"]) == 5
    assert "avant de qualifier" in result["actions"][0]["action"]
    assert result["compensation"] == {"status": "not_assessed"}


def test_old_profile_differs_from_explicit_empty_and_documents_need_review():
    old = inputs()
    del old["profile"]["interventions"]
    assert "historique" in analyze(old, layers(), 1)["unknowns"][0]
    assert "explicitement vide" in analyze(inputs(), layers(), 1)["unknowns"][0]
    doc = {
        "id": "doc:test",
        "quote": "Test fixture only.",
        "project_action": "outdoor_lighting",
        "category": "avoid",
        "sha256": "test-hash",
        "page": 3,
        "species": ["blaireaux"],
        "proposal": "étudier une variante sans éclairage",
    }
    data = inputs(["outdoor_lighting"])
    assert len(analyze(data, layers(), 1, [doc])["actions"]) == 1
    reviewed = deepcopy(doc)
    reviewed["applicability"] = "reviewed"
    result = analyze(data, layers(), 2, [reviewed])
    assert result["actions"][1]["category"] == "avoid"
    assert result["actions"][1]["evidence_status"] == "conditional_proposal"
    assert result["actions"][1]["action"].startswith("Si ")
    assert "doc:test" in result["actions"][1]["source_refs"]
    reviewed["species"] = ["chouette"]
    assert len(analyze(data, layers(), 1, [reviewed])["actions"]) == 1


def test_output_contract_refuses_established_measure_from_map_or_observation_only():
    import pytest
    from pydantic import ValidationError

    from shared.parcels.territorial_schemas import Analysis

    result = analyze(inputs(['fencing']), layers(), 1)
    Analysis.model_validate(result)
    result['actions'][0]['category'] = 'reduce'
    result['actions'][0]['evidence_status'] = 'conditional_proposal'
    with pytest.raises(ValidationError, match='source applicable'):
        Analysis.model_validate(result)
