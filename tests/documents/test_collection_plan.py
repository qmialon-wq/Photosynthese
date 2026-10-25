from shared.documents.schemas import Search
from workers.documents import collection


def test_collection_prioritizes_habitats_and_completes_with_unique_articles(monkeypatch):
    monkeypatch.setattr(collection, "listing", lambda *a, **kw: [{"id": "existing"}])

    class Ingestor:
        def search(self, request, *, stored, total_limit):
            activity = request["search"]["activity"]
            assert not request["collection_target"]
            assert "existing" in stored
            # Le milieu agricole manque de textes : le passage général compense.
            count = min(total_limit, 3) if activity == "agriculture" else total_limit
            identifiers = [f"{activity}-{i}" for i in range(count)]
            stored.update(identifiers)
            return {
                "observed": count,
                "errors": 0,
                "sources_ok": 2,
                "inaccessible": 0,
                "filtered_out": 0,
                "downloaded": count,
                "document_ids": identifiers,
                "downloaded_ids": identifiers,
            }

        def log(self, *args, **kwargs):
            pass

    result = collection.run(
        Ingestor(),
        {
            "collection_target": 100,
            "collection_species": "renards",
            "search": Search(species=["Vulpes vulpes"], max_pages=10).model_dump(),
        },
    )
    assert result["target_reached"] and result["corpus_count"] == 100
    assert result["initial_count"] == 1 and result["downloaded"] == 99
    assert result["passes"] == [
        {"activity": "urban", "downloaded": 25},
        {"activity": "agriculture", "downloaded": 3},
        {"activity": "all", "downloaded": 71},
    ]


def test_collection_already_at_target_makes_no_requests(monkeypatch):
    monkeypatch.setattr(
        collection, "listing", lambda *a, **kw: [{"id": str(i)} for i in range(100)]
    )
    result = collection.run(
        object(),
        {
            "collection_target": 100,
            "collection_species": "renards",
        },
    )
    assert result["target_reached"] and result["downloaded"] == 0


def test_collection_reports_shortfall(monkeypatch):
    monkeypatch.setattr(collection, "listing", lambda *a, **kw: [])

    class Empty:
        def search(self, *args, **kwargs):
            return {
                "observed": 0,
                "errors": 1,
                "sources_ok": 0,
                "inaccessible": 0,
                "filtered_out": 0,
                "downloaded": 0,
                "document_ids": [],
                "downloaded_ids": [],
            }

        def log(self, *args, **kwargs):
            pass

    result = collection.run(
        Empty(),
        {
            "collection_target": 100,
            "collection_species": "renards",
            "search": Search(species=["Vulpes vulpes"]).model_dump(),
        },
    )
    assert not result["target_reached"] and result["corpus_count"] == 0
    assert result["errors"] == 3
