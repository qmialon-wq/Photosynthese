from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import httpx
import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared.documents import service
from shared.documents.schemas import Decision, FullText, Publication, Search, Watch
from workers.documents.http import SafeHTTP
from workers.documents.ingestion import Ingestor
from workers.documents.runtime import execute, publish_pending

pytestmark = pytest.mark.integration


def make_task(kind="search", request=None):
    return service.submit(kind, request or {"search": {"species": ["Vulpes vulpes"]}}, "test")["id"]


def test_doi_identifier_bridge_merges_without_losing_provenance(document_db):
    task = make_task()
    first = service.register(
        Publication(
            source="europepmc", source_id="MED:1", title="Fixture", identifiers={"pmcid": "PMC123"}
        ),
        task,
    )
    second = service.register(
        Publication(
            source="crossref",
            source_id="10.1234/test",
            title="Fixture",
            doi="https://doi.org/10.1234/TEST",
        ),
        task,
    )
    assert first != second
    final = service.register(
        Publication(
            source="openalex",
            source_id="W1",
            title="Fixture",
            doi="10.1234/test",
            identifiers={"pmcid": "PMC123"},
        ),
        task,
    )
    assert str(service.document(first)["id"]) == str(service.document(second)["id"]) == final
    with service.transaction() as connection:
        assert (
            connection.execute(
                "SELECT count(*) n FROM scientific_documents WHERE merged_into IS NULL"
            ).fetchone()["n"]
            == 1
        )
        assert connection.execute("SELECT count(*) n FROM document_provenance").fetchone()["n"] == 3
    service.register(
        Publication(
            source="openalex",
            source_id="W1",
            title="Fixture",
            doi="10.1234/test",
            identifiers={"pmcid": "PMC123"},
        ),
        task,
    )
    with service.transaction() as connection:
        assert connection.execute("SELECT count(*) n FROM document_provenance").fetchone()["n"] == 3


def test_allowed_pdf_is_saved_indexed_deduplicated_and_reviewed(document_db, pdf_bytes):
    task = make_task()
    requested = []
    http = SafeHTTP(
        document_db,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: requested.append(str(request.url))
                or httpx.Response(200, content=pdf_bytes)
            )
        ),
        validate=lambda _: None,
        sleep=lambda _: None,
    )
    identifier = service.register(
        Publication(
            source="openalex",
            source_id="W1",
            title="Fixture",
            doi="10.1234/test",
            fulltexts=[
                FullText(
                    url="https://example.org/fixture.pdf",
                    license="cc-by",
                    evidence="test fixture explicit licence",
                )
            ],
        ),
        task,
    )
    ingestor = Ingestor(document_db, http, task)
    result = ingestor.fetch(identifier)
    assert result["pages"] == 2 and result["chunks"] >= 2
    assert service.document(identifier)["status"] == "indexed"
    ingestor.fetch(identifier)
    assert len(requested) == 1
    with service.transaction() as connection:
        asset = connection.execute("SELECT * FROM document_assets").fetchone()
        assert asset["license"] == "cc-by" and asset["rights_evidence"]["task_id"] == task
        assert (document_db.root / asset["storage_key"]).is_file()
        assert connection.execute("SELECT count(*) n FROM document_pages").fetchone()["n"] == 2
    service.review(identifier, Decision(relevance="accepted", quality="accepted"), "alice")
    with TestClient(app) as client:
        assert len(client.get("/documents?approved_only=true").json()) == 1
        assert client.get(f"/documents/{identifier}/chunks").json()[0]["page_number"] == 1
        assert client.get(f"/documents/{identifier}/assets/{asset['id']}").content == pdf_bytes
        response = client.post(
            f"/documents/{identifier}/review",
            headers={"X-Reviewer": "bob"},
            json={"relevance": "rejected", "quality": "accepted", "note": "Hors contexte local"},
        )
        assert response.json()["status"] == "rejected"
        assert client.get("/documents?approved_only=true").json() == []
        assert len(client.get(f"/documents/{identifier}").json()["reviews"]) == 2
    assert ingestor.fetch(identifier)["skipped"]
    assert len(requested) == 1


def test_unknown_license_never_downloads_and_api_failure_is_isolated(document_db, monkeypatch):
    task = make_task()
    http = SafeHTTP(
        document_db,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: pytest.fail("Aucune requête réseau autorisée dans ce test")
            )
        ),
        validate=lambda _: None,
    )
    identifier = service.register(
        Publication(
            source="openalex",
            source_id="W1",
            title="Fixture",
            fulltexts=[
                FullText(url="https://example.org/paywall", license="unknown", evidence="none")
            ],
        ),
        task,
    )
    ingestor = Ingestor(document_db, http, task)
    assert ingestor.fetch(identifier)["inaccessible"]
    assert service.document(identifier)["status"] == "inaccessible"

    class BrokenSource:
        def __init__(self, _):
            pass

        def search(self, _):
            raise ValueError("Simulated external outage")

    class WorkingSource:
        def __init__(self, _):
            pass

        def search(self, _):
            yield Publication(
                source="crossref", source_id="10.1234/new", doi="10.1234/new", title="Fixture 2"
            )

    monkeypatch.setitem(
        __import__("workers.documents.ingestion", fromlist=["SOURCES"]).SOURCES,
        "openalex",
        BrokenSource,
    )
    monkeypatch.setitem(
        __import__("workers.documents.ingestion", fromlist=["SOURCES"]).SOURCES,
        "crossref",
        WorkingSource,
    )
    result = ingestor.search(
        {"search": {"species": ["Vulpes vulpes"], "sources": ["openalex", "crossref"]}}
    )
    assert result["observed"] == 1 and result["errors"] == 1 and result["sources_ok"] == 1


def test_watches_and_outbox_are_idempotent_and_metadata_jobs_are_async(document_db):
    body = Watch(
        name="Fox ecology",
        search=Search(species=["Vulpes vulpes"]),
        enabled=True,
        interval_seconds=60,
    )
    watch = service.watch(body, "alice")
    assert service.watch(body, "alice")["id"] == watch["id"]
    now = datetime.now(UTC) + timedelta(seconds=1)
    assert service.schedule_due(now) == 1
    assert service.schedule_due(now) == 0
    assert service.schedule_due(now + timedelta(seconds=61)) == 1
    mock = MagicMock()
    assert publish_pending(mock) == 2 and publish_pending(mock) == 0
    with TestClient(app) as client:
        first = client.post(
            "/documents/search",
            json={"species": ["Vulpes vulpes"]},
            headers={"Idempotency-Key": "same"},
        )
        second = client.post(
            "/documents/search",
            json={"species": ["Vulpes vulpes"]},
            headers={"Idempotency-Key": "same"},
        )
        assert first.status_code == 202 and first.json()["id"] == second.json()["id"]
        assert (
            client.post(
                "/documents/search",
                json={"species": ["Sus scrofa"]},
                headers={"Idempotency-Key": "same"},
            ).status_code
            == 409
        )
        assert client.get(first.json()["status_url"]).json()["status"] == "queued"
        assert client.post("/documents/search", json={}).status_code == 422
        assert (
            client.post(
                "/documents/import", json={"path": "../outside.pdf", "rights_confirmed": True}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/documents/upload?filename=test.pdf&rights_confirmed=false", content=b"fake"
            ).status_code
            == 422
        )


def test_manual_import_worker_retry_preserves_one_asset(document_db, pdf_bytes):
    target = document_db.root / "inbox/fixture.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(pdf_bytes)
    with TestClient(app) as client:
        operation = client.post(
            "/documents/import", json={"path": "fixture.pdf", "rights_confirmed": True}
        ).json()
        assert execute(operation["id"], document_db)
        completed = client.get(operation["status_url"]).json()
        assert completed["status"] == "completed", completed["error"]
        assert execute(operation["id"], document_db)
        assert client.get(operation["status_url"]).json()["attempts"] == 1
        retry = client.post(f"/documents/tasks/{operation['id']}/retry").json()
        assert execute(retry["id"], document_db)
        assert client.get(retry["status_url"]).json()["status"] == "completed"
        events = client.get(f"/documents/tasks/{operation['id']}/events").json()
        assert events[0]["stage"] == "start" and events[-1]["stage"] == "finish"
    with service.transaction() as connection:
        assert connection.execute("SELECT count(*) n FROM document_assets").fetchone()["n"] == 1
        assert (
            connection.execute(
                "SELECT count(*) n FROM scientific_documents WHERE merged_into IS NULL"
            ).fetchone()["n"]
            == 1
        )


def test_new_content_requires_quality_review_again(document_db, pdf_bytes):
    task = make_task()
    identifier = service.register(
        Publication(source="manual", source_id="fixture", title="Fixture"), task
    )
    http = SafeHTTP(document_db)
    try:
        ingestor = Ingestor(document_db, http, task)
        asset = ingestor.asset(identifier, pdf_bytes, "pdf", "cc-by", {"fixture": True})
        service.review(identifier, Decision(relevance="accepted", quality="accepted"), "alice")
        assert ingestor.asset(identifier, pdf_bytes, "pdf", "cc-by", {}) == asset
        assert service.document(identifier)["quality"] == "accepted"
        ingestor.asset(identifier, pdf_bytes + b"\n% new version\n", "pdf", "cc-by", {})
        assert service.document(identifier)["quality"] == "pending"
        assert service.document(identifier)["relevance"] == "accepted"
    finally:
        http.close()


def test_xml_copy_needs_article_license_matching_metadata(document_db):
    task = make_task()
    data = b"""<article><front><article-meta><permissions><license>
        <ext-link xmlns:xlink="http://www.w3.org/1999/xlink"
        xlink:href="https://creativecommons.org/licenses/by-nc/4.0/"/>
        </license></permissions></article-meta></front>
        <body><p>Full text</p><license href="https://creativecommons.org/licenses/by/4.0/"/>
        </body></article>"""
    http = SafeHTTP(
        document_db,
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=data))
        ),
        validate=lambda _: None,
    )
    try:
        identifier = service.register(
            Publication(
                source="europepmc",
                source_id="MED:1",
                title="Fixture",
                fulltexts=[
                    FullText(
                        url="https://example.org/article.xml",
                        format="xml",
                        license="cc-by",
                        evidence="Fixture metadata",
                    )
                ],
            ),
            task,
        )
        assert Ingestor(document_db, http, task).fetch(identifier)["inaccessible"]
        with service.transaction() as connection:
            assert connection.execute("SELECT count(*) n FROM document_assets").fetchone()["n"] == 0
    finally:
        http.close()


def test_result_and_finish_event_commit_together(document_db, monkeypatch):
    from workers.documents import runtime

    task = make_task()
    monkeypatch.setattr(runtime.Ingestor, "perform", lambda *_: {"observed": 1})
    original_event = service.event

    def unavailable_journal(identifier, stage, message, **kwargs):
        if stage == "finish":
            raise RuntimeError("Journal unavailable")
        return original_event(identifier, stage, message, **kwargs)

    monkeypatch.setattr(service, "event", unavailable_journal)
    with pytest.raises(RuntimeError, match="Journal unavailable"):
        execute(task, document_db)
    assert service.task(task)["status"] == "running"
    monkeypatch.setattr(service, "event", original_event)
    assert execute(task, document_db)
    assert service.task(task)["status"] == "completed"
    assert service.task(task)["attempts"] == 2
