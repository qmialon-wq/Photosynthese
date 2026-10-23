import json
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared.documents import corpus, service
from shared.documents.schemas import Decision, Publication
from workers.documents.runtime import execute

pytestmark = pytest.mark.integration


def imported_pdf(settings, pdf_bytes):
    path = settings.root / "inbox/corpus.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)
    task = service.submit(
        "import",
        {
            "path": "corpus.pdf",
            "rights_confirmed": True,
            "species": ["renards"],
        },
        "alice",
    )
    assert execute(task["id"], settings)
    finished = service.task(task["id"])
    assert finished["status"] == "completed", finished["error"]
    return finished["result"]["document_id"]


def test_catalog_matches_canonical_classes(document_db):
    manifest = json.loads(
        Path("workers/vision/biosentinelle_vision/manifests/classes-v3-10.json").read_text()
    )
    with TestClient(app) as client:
        result = client.get("/documents/species").json()
    assert [(s["name"], s["scientific_name"], s["class_index"]) for s in result] == [
        (s["name"], s["latin"], s["id"]) for s in manifest["classes"]
    ]
    assert all(s["selected_count"] == 0 for s in result)


def test_import_select_remove_and_persistent_history(document_db, pdf_bytes):
    identifier = imported_pdf(document_db, pdf_bytes)
    with TestClient(app) as client:
        assert len(client.get("/documents?species=renards").json()) == 1
        assert client.get("/documents?selected_only=true").json() == []
        endpoint = f"/documents/{identifier}/species/renards"
        result = client.put(endpoint, json={"enabled": True}, headers={"X-Reviewer": "alice"})
        assert result.status_code == 200
        assert result.json()["species"][0]["available"] is True
        assert len(client.get("/documents?species=renards&selected_only=true").json()) == 1
        assert client.get("/documents?species=blaireaux&selected_only=true").json() == []
        client.put(f"/documents/{identifier}/species/blaireaux", json={"enabled": True})
        client.put(endpoint, json={"enabled": False}, headers={"X-Reviewer": "bob"})
        # Une nouvelle ingestion ne réactive pas une décision de retrait.
        corpus.discover(identifier, ["Vulpes vulpes"], "watch")
        assert client.get("/documents?species=renards&selected_only=true").json() == []
        assert len(client.get("/documents?species=blaireaux&selected_only=true").json()) == 1
        detail = client.get(f"/documents/{identifier}").json()
        assert detail["selection_history"][-1]["actor"] == "bob"
        assert detail["selection_history"][-1]["enabled"] is False
        assert detail["reviews"][0]["actor"] == "alice"
        assert client.get(f"/documents/{identifier}/pages").json()[0]["page_number"] == 1
        original = client.get(
            f"/documents/{identifier}/assets/{detail['assets'][0]['id']}?inline=true"
        )
        assert original.headers["content-disposition"].startswith("inline")
        assert original.headers["content-type"] == "application/pdf"
        assert original.content == pdf_bytes
    service.review(identifier, Decision(relevance="rejected", quality="accepted"), "alice")
    assert corpus.listing(None, True, None, False, 20, 0) == []


def test_metadata_and_empty_pdf_cannot_be_selected(document_db):
    task = service.submit("search", {"search": {"species": ["Vulpes vulpes"]}}, "alice")
    identifier = service.register(
        Publication(source="openalex", source_id="W1", title="Fixture"), task["id"]
    )
    corpus.discover(identifier, ["Vulpes vulpes"], "alice")
    with TestClient(app) as client:
        assert (
            client.put(
                f"/documents/{identifier}/species/renards", json={"enabled": True}
            ).status_code
            == 409
        )
        assert (
            client.put(
                f"/documents/{identifier}/species/unknown", json={"enabled": False}
            ).status_code
            == 422
        )
        assert client.get("/documents?species=unknown").status_code == 422
        assert len(client.get("/documents?species=renards").json()) == 1
    # Même une incohérence de statut ne permet pas d'inclure une notice sans passages.
    with service.transaction() as connection:
        connection.execute(
            "UPDATE scientific_documents SET processing_status='indexed' WHERE id=%s", (identifier,)
        )
    with TestClient(app) as client:
        assert (
            client.put(
                f"/documents/{identifier}/species/renards", json={"enabled": True}
            ).status_code
            == 409
        )


def test_merge_preserves_latest_human_exclusion(document_db, pdf_bytes):
    first = imported_pdf(document_db, pdf_bytes)
    corpus.select(first, "renards", True, "alice")
    task = service.submit("search", {}, "alice")["id"]
    second = service.register(Publication(source="openalex", source_id="W1", title="Fixture"), task)
    corpus.select(second, "renards", False, "bob")
    with service.transaction(write=True) as connection:
        service.merge(connection, first, second)
    assert corpus.links(first)[0]["enabled"] is False
    assert corpus.links(first)[0]["actor"] == "bob"
    with TestClient(app) as client:
        detail = client.get(f"/documents/{second}").json()
        assert detail["id"] == first
        assert len(detail["selection_history"]) == 2
