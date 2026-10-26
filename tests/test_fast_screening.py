from workers.documents.screening import screen


def test_scans_every_passage_and_preserves_an_adverse_result():
    recommendation = (
        "We recommend preserving hedgerows in agricultural landscapes "
        "to maintain habitat connectivity."
    )
    adverse = (
        "However, there is no evidence that hedgerow restoration "
        "benefits every species in urban habitats."
    )
    rows = [
        {
            "id": str(i),
            "text": text,
            "page_number": i + 1,
            "asset_id": "a",
            "sha256": "hash",
            "license": "cc-by",
            "source_url": "local",
        }
        for i, text in enumerate([recommendation] * 90 + [adverse])
    ]
    visited = []

    def stream():
        for row in rows:
            visited.append(row["id"])
            yield row

    result = screen({"id": "d", "chunk_count": len(rows)}, stream(), lambda *a, **kw: None)
    assert len(visited) == result["chunks_read"] == 91
    quotes = {f["quote"] for f in result["findings"]}
    assert quotes == {recommendation, adverse}
    assert any(f["role"] == "limitation" for f in result["findings"])
    assert all(f["quote"] in rows[int(f["chunk_id"])]["text"] for f in result["findings"])


def test_irrelevant_text_is_audited_without_forcing_a_recommendation():
    result = screen({"id": "d", "chunk_count": 0}, iter([]), lambda *a, **kw: None)
    assert result["findings"] == []
    assert result["chunks_read"] == 0


def test_balanced_pipeline_never_calls_model_for_document_reading(monkeypatch, tmp_path):
    from shared.rag.config import RagSettings
    from tests.test_synthesis_contracts import FakeGenerator, fixtures
    from workers.documents import synthesis

    context = fixtures(monkeypatch, tmp_path)
    generator = FakeGenerator()
    result = synthesis.synthesize(
        {}, context, RagSettings(reading_mode="balanced"), lambda *a, **kw: None, generator
    )
    assert not generator.seen
    assert result["coverage"]["chunks_read"] == 24
    assert result["coverage"]["documents_read"] == 2
    assert result["coverage"]["reading_mode"] == "balanced"
    assert result["status"] == "generated"
    assert len(result["pages"]) == 4


def test_failed_batch_is_rejected_and_reported_instead_of_published(monkeypatch, tmp_path):
    from shared.rag.config import RagSettings
    from shared.rag.synthesis import Actions
    from tests.test_synthesis_contracts import FakeGenerator, action, fixtures
    from workers.documents import synthesis

    class Unsupported(FakeGenerator):
        def generate(self, instruction, payload, schema):
            if schema is Actions:
                return Actions(actions=[action(["D999"])])
            raise AssertionError("No page should be written from rejected proposals")

    context = fixtures(monkeypatch, tmp_path)
    result = synthesis.synthesize({}, context, RagSettings(), lambda *a, **kw: None, Unsupported())
    assert result["status"] == "no_actionable_evidence"
    assert result["coverage"]["batches_rejected"][0]["batch"] == 1
    assert not result["coverage"]["recommendation_coverage_complete"]


def test_consolidation_shortlist_is_bounded_and_preserves_distinct_themes():
    import json

    from tests.test_synthesis_contracts import action
    from workers.documents.screening import shortlist

    vegetation = {"action_type": "territorial", **action()}
    lighting = {
        **vegetation,
        "action": "Limiter l’éclairage près des habitats existants.",
        "citations": ["D2"],
    }
    selected = shortlist([{"actions": [vegetation] * 100 + [lighting]}])
    actions = [a for b in selected for a in b["actions"]]
    assert len(actions) == 2
    assert {c for a in actions for c in a["citations"]} == {"D1", "D2"}
    assert sum(len(json.dumps(a, ensure_ascii=False)) for a in actions) <= 8000
