"""RAG safety contracts run without PostgreSQL, network, encoder or GPU."""

import pytest
from pydantic import ValidationError

from shared.rag.config import RagSettings
from shared.rag.schemas import Context, Filters, Report, Search
from workers.documents.embeddings import manifest, version
from workers.documents.rag import fidelity, report


def test_no_sources_abstains_without_observations_or_generation():
    result = report(
        Report(question="Comment préserver les haies ?"),
        {
            "status": "no_sources",
            "hits": [],
            "question": "Comment préserver les haies ?",
        },
    )
    assert result["recommendation_status"] == "abstained"
    assert not result["inferred_recommendations"]
    assert not result["observed_facts"]
    assert result["generation_enabled"] is False


def test_query_validation_and_unknown_generation_options():
    with pytest.raises(ValidationError):
        Search(question="question", llm=True)
    with pytest.raises(ValidationError):
        Filters(published_after="2026-01-01", published_before="2020-01-01")
    with pytest.raises(ValidationError):
        Context(latitude=49.1, provenance="fixture")
    with pytest.raises(ValidationError):
        Context(observed_at="2026-01-01T10:00:00", provenance="fixture")


def test_model_manifest_version_tracks_entire_configuration():
    data = manifest(RagSettings())
    assert version(data) != version({**data, "query_prefix": "different: "})
    assert version(data) != version({**data, "revision": "a" * 40})
    assert RagSettings(model_manifest="").model_manifest is None


def test_fidelity_does_not_confuse_quoting_with_scientific_entailment():
    hit = {"citation": "S1", "chunk_id": "c1", "text": "An exact excerpt."}
    assert (
        fidelity({"hits": [hit], "publication_evidence": [hit]})["verbatim_citation_precision"]
        == 1.0
    )
    assert (
        fidelity({"hits": [hit], "publication_evidence": [{**hit, "citation": "invented"}]})[
            "invalid_citations"
        ]
        == 1
    )
    assert fidelity({"hits": [], "publication_evidence": []})["verbatim_citation_precision"] is None
