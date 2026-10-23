"""Synthetic vectors are used only in tests; real model smoke is opt-in."""

import hashlib
from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared.documents import corpus, service
from shared.documents.schemas import Publication
from shared.rag.config import RagSettings
from shared.rag.export import markdown
from shared.rag.schemas import DocumentContext, Evaluation, Filters, Index, Report, Search
from shared.rag.service import document_context
from workers.documents import embeddings, rag, retrieval
from workers.documents.runtime import execute

pytestmark = pytest.mark.integration


class TestEncoder:
    __test__ = False
    version = "test-only-encoder-v1"
    manifest = {"dimension": 3, "name": "synthetic-tests-only"}

    def encode(self, text, *, query=False):
        return [1.0, 0.0, 0.0] if "hedgerow" in text.lower() else [0.0, 1.0, 0.0]


def publication(text="Hedgerow conservation benefits the red fox.", *, approved=True, doi=None):
    identifier = service.register(
        Publication(
            source="manual",
            source_id=str(uuid4()),
            title="Synthetic ecological fixture",
            doi=doi,
            published_date="2024-06-15",
            authors=["Test Author"],
        ),
        None,
    )
    corpus.discover(identifier, ["Vulpes vulpes"], "test")
    asset, chunk = str(uuid4()), str(uuid4())
    with service.transaction() as connection:
        connection.execute(
            """INSERT INTO document_assets(id,document_id,sha256,storage_key,format,license,
            rights_evidence,byte_size) VALUES(%s,%s,%s,'test.pdf','pdf','cc-by','{}',10)""",
            (asset, identifier, hashlib.sha256(asset.encode()).hexdigest()),
        )
        connection.execute(
            "INSERT INTO document_pages VALUES(%s,3,%s,%s,'en','[]')",
            (asset, text, text),
        )
        connection.execute(
            """INSERT INTO document_chunks(id,asset_id,page_number,ordinal,start_char,end_char,
            text,language,is_reference) VALUES(%s,%s,3,0,0,%s,%s,'en',false)""",
            (chunk, asset, len(text), text),
        )
        connection.execute(
            "UPDATE scientific_documents SET processing_status='indexed' WHERE id=%s", (identifier,)
        )
    if approved:
        corpus.select(identifier, "renards", True, "ecologist")
    return identifier, chunk


def test_index_hybrid_filters_sources_and_revocation(document_db):
    identifier, chunk = publication(doi="10.1234/rag-fixture")
    publication(approved=False)
    irrelevant, _ = publication("Bartonella infection in a wild carnivore.")
    model = TestEncoder()
    settings = RagSettings(min_similarity=0.9)
    indexed = retrieval.index(Index(), settings, model)
    assert indexed["embedded"] == 2
    assert retrieval.index(Index(), settings, model)["cached"] == 2
    request = Search(question="hedgerow", filters=Filters(species=["renards"]))
    result = retrieval.retrieve(request, settings, model)
    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["chunk_id"] == chunk and hit["page"] == 3
    assert hit["doi"] == "10.1234/rag-fixture" and hit["provenance"][0]["source"] == "manual"
    assert hit["channels"] == ["lexical", "vector"]
    assert hit["similarity"] == pytest.approx(1.0)
    assert irrelevant != hit["document_id"]
    document_context(
        identifier,
        DocumentContext(
            habitats=["hedgerow"],
            territories=["Normandie"],
            provenance="Lecture du texte synthétique",
        ),
        "alice",
    )
    assert retrieval.retrieve(
        request.model_copy(
            update={
                "filters": Filters(
                    species=["renards"],
                    habitat="hedgerow",
                    territory="Normandie",
                    sources=["manual"],
                    published_after="2024-06-01",
                    published_before="2024-06-30",
                )
            }
        ),
        settings,
        model,
    )["hits"]
    assert not retrieval.retrieve(
        request.model_copy(update={"filters": Filters(territory="Bretagne")}), settings, model
    )["hits"]
    assert not retrieval.retrieve(
        request.model_copy(update={"filters": Filters(published_before="2024-06-01")}),
        settings,
        model,
    )["hits"]
    corpus.select(identifier, "renards", False, "bob")
    assert retrieval.retrieve(request, settings, model)["status"] == "no_sources"


def test_version_dedup_and_stale_text_not_retrieved(document_db):
    identifier, chunk = publication()
    publication()
    settings, model = RagSettings(), TestEncoder()
    retrieval.index(Index(), settings, model)
    request = Search(question="hedgerow")
    assert len(retrieval.retrieve(request, settings, model)["hits"]) == 1
    with service.transaction() as connection:
        connection.execute("UPDATE document_chunks SET text='different' WHERE id=%s", (chunk,))
    assert all(h["chunk_id"] != chunk for h in retrieval.retrieve(request, settings, model)["hits"])
    model.version = "test-only-encoder-v2"
    assert retrieval.retrieve(request, settings, model)["status"] == "no_sources"
    assert retrieval.index(Index(document_ids=[identifier]), settings, model)["embedded"] == 1


def test_async_api_without_encoder_llm_and_export(document_db, monkeypatch):
    identifier, chunk = publication()
    # Lexical mode does not call any ML dependency or network service.
    monkeypatch.setattr(retrieval, "load", lambda *_: pytest.fail("Unexpected model loading"))
    with TestClient(app) as client:
        posted = client.post(
            "/rag/recommendations", json={"question": "hedgerow", "mode": "lexical"}
        )
        assert posted.status_code == 202
        task = posted.json()["id"]
        assert execute(task, document_db)
        status = client.get(f"/documents/tasks/{task}").json()
        assert status["status"] == "completed", status
        run = client.get(status["result"]["result_url"]).json()
        result = run["result"]
        assert result["generation_enabled"] is False
        assert result["publication_evidence"][0]["chunk_id"] == chunk
        assert not result["inferred_recommendations"]
        assert result["fidelity"]["verbatim_citation_precision"] == 1.0
        exported = client.get(f"/rag/runs/{run['id']}/export?format=markdown")
        assert exported.status_code == 200 and chunk in exported.text and "[S1]" in exported.text
        assert client.get(f"/rag/runs/{run['id']}/export").json()["result"] == result
        assert (
            client.post("/rag/search", json={"question": "hedgerow", "llm": True}).status_code
            == 422
        )
    empty = retrieval.retrieve(Search(question="ocean", mode="lexical"), RagSettings())
    absent = rag.report(Report(question="ocean", mode="lexical"), empty)
    assert absent["status"] == "no_sources" and absent["recommendation_status"] == "abstained"
    assert not absent["next_steps"] and not absent["publication_evidence"]
    assert "Aucune" in markdown(absent)


def test_evaluation_and_fidelity_detect_invalid_citation(document_db):
    _, chunk = publication()
    result = rag.evaluate(
        Evaluation(
            cases=[
                {
                    "search": {"question": "hedgerow", "mode": "lexical", "limit": 1},
                    "relevant_chunks": [chunk],
                }
            ]
        ),
        RagSettings(),
    )
    assert all(v == 1.0 for v in result["metrics"].values())
    assert result["cases"][0]["fidelity"]["invalid_citations"] == 0
    tampered = {
        "hits": [{"citation": "S1", "text": "original", "chunk_id": chunk}],
        "publication_evidence": [{"citation": "S1", "text": "invented", "chunk_id": chunk}],
    }
    assert rag.fidelity(tampered)["invalid_citations"] == 1


def test_model_integrity_and_missing_files_no_download(document_db, tmp_path):
    settings = RagSettings(model_root=tmp_path)
    with pytest.raises(ValueError, match="rag-prepare"):
        embeddings.OnnxEncoder(settings)
    data = embeddings.manifest(settings)
    assert data["dimension"] == 384
    assert len(embeddings.version(data)) == 64

    class CorruptHTTP:
        def get(self, *args, **kwargs):
            return b"not ONNX", {}, ""

    with pytest.raises(ValueError, match="Intégrité"):
        embeddings.prepare(settings, CorruptHTTP())
    assert not list(tmp_path.rglob("*.onnx"))


@pytest.mark.real_model
def test_real_multilingual_encoder_cpu(document_db):
    model = embeddings.load(RagSettings())
    query = model.encode("Préserver les haies pour les renards", query=True)
    matching = model.encode("Hedgerow conservation protects red fox habitat.")
    unrelated = model.encode("Clinical cardiac surgery in human hospital patients.")
    assert len(query) == 384

    def similarity(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert similarity(query, matching) > similarity(query, unrelated)
    assert model.encode("hedgerow " * 800)  # No silent truncation / overflow.
    _, chunk = publication("Hedgerow conservation protects red fox habitat.")
    settings = RagSettings()
    retrieval.index(Index(), settings, model)
    result = retrieval.retrieve(
        Search(question="Préserver les haies pour les renards"), settings, model
    )
    assert result["hits"] and result["hits"][0]["chunk_id"] == chunk
    assert result["hits"][0]["similarity"] >= settings.min_similarity


def test_only_current_human_validations_are_observations(document_db):
    from shared.rag import service as rag_service

    with service.transaction() as connection:
        connection.execute("INSERT INTO review_groups(id,split) VALUES('g','train')")
        connection.execute("""INSERT INTO review_videos
            (id,group_id,source_key,original_name,candidates)
            VALUES('v','g','v.mp4','renard.mp4','[]')""")
        connection.execute("""INSERT INTO review_frames
            (id,video_id,frame_index,time_seconds,image_key,sha256,width,height,quality)
            VALUES('f','v',0,0,'frame.jpg','sha',100,100,'{}')""")
        for sample, state in (("uncertain", "pending"), ("human", "validated"), ("no", "rejected")):
            connection.execute(
                """INSERT INTO review_samples(id,frame_id,original_box,
                original_crop_key,detector_identity,detection_score,predicted_label,
                classification_score) VALUES(%s,'f','{}','crop.jpg','md',0.9,'renards',0.1)""",
                (sample,),
            )
            connection.execute(
                """INSERT INTO review_revisions(sample_id,revision,state,label,box,
                recipe,render_status,actor,provenance)
                VALUES(%s,0,%s,%s,'{}','{}','ready','alice','{}')""",
                (sample, state, "renards" if state == "validated" else None),
            )
    with TestClient(app) as client:
        response = client.put(
            "/rag/videos/v/context",
            json={
                "observed_at": "2026-10-01T10:00:00Z",
                "latitude": 49.1,
                "longitude": 0.2,
                "territory": "Normandie",
                "provenance": "Site test",
            },
        )
        assert response.status_code == 200
    rows = rag_service.observations(["v"], ["renards"])
    assert len(rows) == 1 and rows[0]["sample_id"] == "human"
    assert rows[0]["original_prediction_score"] == 0.1
    assert rows[0]["context"]["territory"] == "Normandie"
    assert rows[0]["cd_nom"] is None
