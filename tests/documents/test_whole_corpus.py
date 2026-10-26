import pytest

from shared.documents import corpus, service
from workers.documents import synthesis

from .test_rag import publication

pytestmark = pytest.mark.integration


def test_dossiers_have_priority_over_queued_translations(document_db, monkeypatch):
    from workers.documents import runtime

    service.submit("translate", {"document_id": "fixture"}, "test")
    report = service.submit("rag", {"action": "parcel", "body": {}}, "test")
    executed = []
    monkeypatch.setattr(
        runtime, "execute", lambda identifier, settings: executed.append(identifier) or True
    )
    assert runtime.execute_priority_report(document_db)
    assert executed == [report["id"]]


def test_all_linked_texts_include_pending_but_exclude_withdrawn_and_rejected(document_db):
    accepted, accepted_chunk = publication("Preserving hedgerows supports wildlife.")
    pending, pending_chunk = publication("Urban fox ecology and movement.", approved=False)
    withdrawn, _ = publication("Withdrawn article.")
    rejected, _ = publication("Rejected article.")
    unrelated, _ = publication("Article associated only with badgers.", approved=False)
    corpus.select(withdrawn, "renards", False, "test")
    with service.transaction() as connection:
        connection.execute(
            "UPDATE scientific_documents SET relevance='rejected' WHERE id=%s", (rejected,)
        )
        connection.execute(
            "UPDATE document_species SET species='blaireaux' WHERE document_id=%s", (unrelated,)
        )
    docs = synthesis.corpus(["renards"])
    assert {d["id"] for d in docs} == {accepted, pending}
    actual = {r["id"] for d in docs for r in synthesis.chunks(d)}
    assert actual == {accepted_chunk, pending_chunk}
    assert service.document(pending)["relevance"] == "pending"
    assert synthesis.corpus([]) == []


def test_corpus_counts_each_passage_once_and_keeps_documents_without_text(document_db):
    from uuid import uuid4

    first, _ = publication()
    empty, _ = publication(approved=False)
    with service.transaction() as connection:
        connection.execute(
            "DELETE FROM document_chunks WHERE asset_id IN "
            "(SELECT id FROM document_assets WHERE document_id=%s)",
            (empty,),
        )
        asset = connection.execute(
            "SELECT asset_id FROM document_chunks WHERE asset_id IN "
            "(SELECT id FROM document_assets WHERE document_id=%s)",
            (first,),
        ).fetchone()["asset_id"]
        for ordinal, reference in [(1, False), (2, True)]:
            connection.execute(
                """INSERT INTO document_chunks
                (id,asset_id,page_number,ordinal,start_char,end_char,text,language,is_reference)
                VALUES(%s,%s,3,%s,0,4,'text','en',%s)""",
                (str(uuid4()), asset, ordinal, reference),
            )
        connection.execute(
            """INSERT INTO document_species(document_id,species,origin,actor)
            VALUES(%s,'blaireaux','human','test')""",
            (first,),
        )
    docs = {d["id"]: d for d in synthesis.corpus(["renards", "blaireaux"])}
    assert set(docs) == {first, empty}
    assert docs[first]["chunk_count"] == 2
    assert set(docs[first]["species"]) == {"renards", "blaireaux"}
    assert docs[empty]["chunk_count"] == 0


def test_dossier_generation_and_four_page_export_use_whole_linked_corpus(
    document_db,
    tmp_path,
    monkeypatch,
):
    from app.main import app
    from fastapi.testclient import TestClient

    from shared.parcels import service as parcels
    from tests.test_synthesis_contracts import FakeGenerator
    from workers.documents.runtime import execute

    from .test_parcels import save_profile, video_and_analysis

    first, _ = publication("We recommend preserving hedgerows in agricultural landscapes.")
    pending, _ = publication(
        "We recommend reducing artificial lighting near hedgerows.", approved=False
    )
    video, analysis = video_and_analysis(
        tmp_path,
        monkeypatch,
        frames=[
            {
                "detections": [
                    {
                        "state": "species_recognized",
                        "classification": {
                            "label": "renards",
                            "score": 0.95,
                        },
                    }
                ],
            }
        ],
    )
    monkeypatch.setenv("BIOSENTINELLE_RAG_GENERATION_ENABLED", "true")
    monkeypatch.setattr(synthesis, "Generator", lambda settings: FakeGenerator())
    with TestClient(app) as client:
        save_profile(client, video)
        job = client.post(
            f"/parcels/videos/{video}/dossiers",
            json={
                "analysis_id": analysis,
                "profile_revision": 1,
            },
        ).json()
        parcels.schedule()
        task = str(parcels.dossier(job["id"])["task_id"])
        assert execute(task, document_db)
        dossier = parcels.dossier(job["id"])
        assert dossier["status"] == "completed", service.task(task)["error"]
        result = dossier["result"]
        assert result["status"] == "generated_recommendations"
        assert {s["document_id"] for s in result["sources"]} == {first, pending}
        assert result["corpus_coverage"]["documents_read"] == 2
        assert result["corpus_coverage"]["documents_pending_review"] == 1
        assert service.document(pending)["relevance"] == "pending"
        assert len(result["territorial_report"]["pages"]) == 4
        html = client.get(f"/parcels/dossiers/{job['id']}/export?format=html")
        assert html.status_code == 200 and html.text.count('<section class="page">') == 4
        assert "default-src 'none'" in html.headers["content-security-policy"]
        text = client.get(f"/parcels/dossiers/{job['id']}/export").text
        assert "Fiches de mise en œuvre" in text and "Page 4/4" in text
