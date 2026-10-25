from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared.documents import corpus, service
from shared.documents.schemas import Publication
from workers.documents import translation
from workers.documents.http import SafeHTTP
from workers.documents.runtime import execute

pytestmark = pytest.mark.integration


def imported(settings, data, name="fixture.pdf", species=None):
    path = settings.root / "inbox" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    job = service.submit(
        "import",
        {"path": name, "rights_confirmed": True, "species": species or ["renards", "blaireaux"]},
        "test",
    )
    assert execute(job["id"], settings)
    finished = service.task(job["id"])
    assert finished["status"] == "completed", finished["error"]
    return finished["result"]["document_id"]


def test_collection_all_species_is_async_and_deduplicates_active_tasks(document_db):
    with TestClient(app) as client:
        first = client.post("/documents/collect", json={"species": []})
        assert first.status_code == 202
        jobs = first.json()["tasks"]
        assert len(jobs) == 10 and len({j["id"] for j in jobs}) == 10
        again = client.post(
            "/documents/collect", json={"species": ["renards", "blaireaux"]}
        ).json()["tasks"]
        assert {j["id"] for j in again}.issubset({j["id"] for j in jobs})
        task = client.get(f"/documents/tasks/{jobs[0]['id']}").json()
        assert task["status"] == "queued"
        assert task["request"]["search"]["download_fulltext"] is True
        assert task["request"]["search"]["focus"] == "human_activities"
        assert task["request"]["collection_target"] == 100
        assert task["request"]["search"]["max_pages"] == 10
        assert client.post("/documents/collect", json={"species": ["unknown"]}).status_code == 422


def test_only_downloaded_documents_and_atomic_removal_per_species(document_db, pdf_bytes):
    first = imported(document_db, pdf_bytes)
    second = imported(document_db, pdf_bytes + b"\n% another version\n", "second.pdf")
    job = service.submit("search", {}, "test")["id"]
    service.register(
        Publication(source="openalex", source_id="metadata-only", title="No file"), job
    )
    with TestClient(app) as client:
        assert len(client.get("/documents?stored_only=true").json()) == 2
        assert len(client.get("/documents").json()) == 3
        result = client.post(
            "/documents/remove",
            json={"species": "renards", "documents": [first, second]},
            headers={"X-Reviewer": "alice"},
        )
        assert result.status_code == 200
        assert client.get("/documents?species=renards&stored_only=true").json() == []
        assert len(client.get("/documents?species=blaireaux&stored_only=true").json()) == 2
        corpus.discover(first, ["Vulpes vulpes"], "automatic")
        assert client.get("/documents?species=renards&stored_only=true").json() == []
        record = client.get(f"/documents/{first}").json()
        assert record["selection_history"][-1]["actor"] == "alice"
        assert (
            client.get(f"/documents/{first}/assets/{record['assets'][0]['id']}").content
            == pdf_bytes
        )
        assert (
            client.post(
                "/documents/remove", json={"species": "geai", "documents": [first]}
            ).status_code
            == 422
        )


def test_translation_resumes_by_page_without_modifying_original(
    document_db, pdf_bytes, monkeypatch
):
    identifier = imported(document_db, pdf_bytes)
    calls = []
    fail = True

    class TestOnlyTranslator:
        def translate(self, text):
            nonlocal fail
            calls.append(text)
            if fail and len(calls) == 3:
                raise RuntimeError("Test interruption")
            return "Traduction de fixture : " + text

    monkeypatch.setattr(translation, "prepare_model", lambda *_: Path("test-only"))
    monkeypatch.setattr(translation, "engine", lambda *_: TestOnlyTranslator())
    job = service.submit("translate", {"document_id": identifier}, "test")["id"]
    http = SafeHTTP(document_db)
    try:
        with pytest.raises(RuntimeError, match="Test interruption"):
            translation.run(identifier, document_db, http, job)
        assert service.document(identifier)["metadata"]["translation_fr"]["status"] == "error"
        fail = False
        translation.run(identifier, document_db, http, job)
    finally:
        http.close()
    with service.transaction() as connection:
        rows = connection.execute(
            "SELECT * FROM document_page_translations ORDER BY page_number"
        ).fetchall()
        assert len(rows) == 2
        assert calls.count(rows[0]["source_text"]) == 1  # Première page déjà persistée.
    with TestClient(app) as client:
        pages = client.get(f"/documents/{identifier}/pages").json()
        assert pages[0]["clean_text"] == rows[0]["source_text"]
        assert pages[0]["translated_text"].startswith("Traduction de fixture")
        assert client.get(f"/documents/{identifier}/translation").status_code == 200
        first = client.post(f"/documents/{identifier}/translate").json()
        second = client.post(f"/documents/{identifier}/translate").json()
        assert first["id"] == second["id"]
    assert service.document(identifier)["quality"] == "pending"  # Pas de fausse revue humaine.


def test_french_original_and_corrupt_model_do_not_trigger_download(document_db, monkeypatch):
    text = (
        "Ce document synthétique décrit les effets des routes et les passages adaptés aux animaux. "
        * 5
    )
    identifier = imported(document_db, text.encode(), "francais.txt")
    job = service.submit("translate", {"document_id": identifier}, "test")["id"]
    http = SafeHTTP(document_db)
    try:
        assert translation.run(identifier, document_db, http, job)["original_fr"]
        document_db.translation_model_root = document_db.root / "models"
        document_db.translation_model_root.mkdir(parents=True)
        (document_db.translation_model_root / "translate-en_fr-1_9.argosmodel").write_bytes(
            b"corrupt"
        )
        with pytest.raises(ValueError, match="corrompue"):
            translation.prepare_model(document_db, http)
    finally:
        http.close()


def test_failed_download_is_hidden_and_next_candidate_is_downloaded(
    document_db, pdf_bytes, monkeypatch
):
    import httpx

    from shared.documents.schemas import FullText
    from workers.documents import ingestion

    class Source:
        def __init__(self, _):
            pass

        def search(self, _):
            for key in ("unavailable", "available"):
                yield Publication(
                    source="openalex",
                    source_id=key,
                    title="Road impacts and wildlife crossings " + key,
                    fulltexts=[
                        FullText(
                            url=f"https://example.test/{key}.pdf",
                            license="cc-by",
                            evidence="Fixture",
                        )
                    ],
                )

    monkeypatch.setitem(ingestion.SOURCES, "openalex", Source)
    request = {
        "search": {
            "species": ["Vulpes vulpes"],
            "sources": ["openalex"],
            "download_fulltext": True,
            "limit_per_source": 1,
        }
    }
    task = service.submit("search", request, "test")["id"]
    http = SafeHTTP(
        document_db,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: (
                    httpx.Response(404)
                    if "unavailable" in str(request.url)
                    else httpx.Response(200, content=pdf_bytes)
                )
            )
        ),
        validate=lambda _: None,
        sleep=lambda _: None,
    )
    try:
        result = ingestion.Ingestor(document_db, http, task).search(request)
    finally:
        http.close()
    assert result["downloaded"] == 1 and result["inaccessible"] == 1
    with TestClient(app) as client:
        rows = client.get("/documents?stored_only=true&species=renards").json()
        assert len(rows) == 1 and rows[0]["title"].endswith(" available")


def test_duplicates_across_sources_do_not_fill_collection_budget(document_db, monkeypatch):
    from shared.documents.schemas import FullText, Search
    from workers.documents import ingestion

    class Source:
        def __init__(self, _):
            pass

        def search(self, _):
            for key in ("same", "same", "second"):
                yield Publication(
                    source="openalex",
                    source_id=key,
                    title="Urban fox ecology " + key,
                    fulltexts=[
                        FullText(
                            url=f"https://example.test/{key}.pdf",
                            license="cc-by",
                            evidence="Fixture",
                        )
                    ],
                )

    for name in ("openalex", "europepmc"):
        monkeypatch.setitem(ingestion.SOURCES, name, Source)
    fetched = []
    monkeypatch.setattr(
        ingestion.Ingestor, "fetch", lambda self, identifier: fetched.append(identifier) or {}
    )
    request = {
        "search": Search(
            species=["Vulpes vulpes"],
            sources=["openalex", "europepmc"],
            limit_per_source=1,
            download_fulltext=True,
        ).model_dump()
    }
    task = service.submit("search", request, "test")["id"]
    http = SafeHTTP(document_db)
    try:
        result = ingestion.Ingestor(document_db, http, task).search(
            request,
            stored=set(),
            total_limit=2,
        )
    finally:
        http.close()
    assert result["downloaded"] == 2
    assert len(fetched) == len(set(fetched)) == 2


def test_identical_files_without_doi_count_once(document_db, pdf_bytes, monkeypatch):
    import httpx

    from shared.documents.schemas import FullText, Search
    from workers.documents import ingestion

    class Source:
        def __init__(self, _):
            pass

        def search(self, _):
            for key in ("first", "second"):
                yield Publication(
                    source="openalex",
                    source_id=key,
                    title="Urban ecology " + key,
                    fulltexts=[
                        FullText(
                            url=f"https://example.test/{key}.pdf",
                            license="cc-by",
                            evidence="Fixture",
                        )
                    ],
                )

    monkeypatch.setitem(ingestion.SOURCES, "openalex", Source)
    request = {
        "search": Search(
            species=["Vulpes vulpes"],
            sources=["openalex"],
            limit_per_source=2,
            download_fulltext=True,
        ).model_dump()
    }
    task = service.submit("search", request, "test")["id"]
    http = SafeHTTP(
        document_db,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=pdf_bytes),
            )
        ),
        validate=lambda _: None,
        sleep=lambda _: None,
    )
    try:
        result = ingestion.Ingestor(document_db, http, task).search(
            request, stored=set(), total_limit=2
        )
    finally:
        http.close()
    assert result["downloaded"] == 1
    assert len(corpus.listing("renards", False, None, False, 100, 0, stored_only=True)) == 1
