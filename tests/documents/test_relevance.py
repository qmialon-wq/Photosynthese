import pytest

from shared.documents.relevance import screen
from shared.documents.schemas import Publication, Search
from workers.documents.sources import retrieval_limit, terms


def publication(title: str, abstract: str | None = None) -> Publication:
    return Publication(source="openalex", source_id="W-fixture", title=title, abstract=abstract)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Road mortality increases despite mitigation measures in Vulpes vulpes", True),
        ("Wildlife crossings reduce road disturbance", True),
        ("Effects of urban development on nocturnal activity", True),
        ("Éclairage routier : effets sur l'activité des renards", True),
        ("Les haies améliorent la survie des geais", True),
        ("Diet and habitat use of suburban Vulpes vulpes", True),
        ("Population ecology of Capreolus capreolus in cropland", True),
        ("Babesia infection in red foxes: a clinical study", False),
        ("Road engineering materials and asphalt properties", False),
        ("Broad ecological effects in Vulpes vulpes", False),
    ],
)
def test_candidate_filter_retains_negative_results_without_claiming_safety(title, expected):
    result = screen(publication(title), Search(species=["Vulpes vulpes"], focus="human_activities"))
    assert result["candidate"] is expected
    assert result["scope"] == "title_and_abstract"
    assert "safe" not in result


def test_selected_activity_and_bounded_queries():
    query = Search(
        species=["Vulpes vulpes"],
        focus="human_activities",
        activity="lighting",
        limit_per_source=50,
    )
    assert not screen(publication("Road mortality and mitigation"), query)["candidate"]
    assert screen(publication("Artificial lighting", "Nocturnal activity is disturbed."), query)[
        "candidate"
    ]
    boolean = terms(query, boolean=True)
    assert (
        '"Vulpes vulpes"' in boolean
        and '"artificial light"' in boolean
        and '"mitigation"' in boolean
    )
    assert boolean.count(" AND ") == 2
    assert "wildlife impact mitigation" in terms(query)
    assert retrieval_limit(query) == 100
    assert terms(Search(species=["Vulpes vulpes"]), boolean=True) == '("Vulpes vulpes")'


@pytest.mark.integration
def test_screening_before_storage_and_download_with_traceable_results(document_db, monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient

    from shared.documents import service
    from workers.documents import ingestion
    from workers.documents.http import SafeHTTP

    class Source:
        def __init__(self, _):
            pass

        def search(self, _):
            for index, title in enumerate(
                [
                    "Clinical babesiosis in foxes",
                    "Road asphalt engineering",
                    "Road mortality increases despite mitigation measures in foxes",
                ]
            ):
                yield Publication(source="crossref", source_id=f"fixture-{index}", title=title)

    monkeypatch.setitem(ingestion.SOURCES, "crossref", Source)
    query = Search(
        species=["Vulpes vulpes"],
        sources=["crossref"],
        focus="human_activities",
        activity="transport",
        limit_per_source=1,
    )
    task = service.submit("search", {"search": query.model_dump()}, "test")["id"]
    old_id = service.register(publication("Previously discovered clinical paper"), task)
    http = SafeHTTP(document_db)
    try:
        result = ingestion.Ingestor(document_db, http, task).search({"search": query.model_dump()})
    finally:
        http.close()
    assert result["filtered_out"] == 2 and result["observed"] == 1 and result["errors"] == 0
    assert service.document(old_id)["title"] == "Previously discovered clinical paper"
    with TestClient(app) as client:
        targeted = client.get("/documents?focus_only=true&species=renards").json()
        assert len(targeted) == 1 and "mortality increases" in targeted[0]["title"]
        assert targeted[0]["metadata"]["screening"]["candidate"] is True
        assert client.get("/documents?selected_only=true").json() == []
        journal = client.get(f"/documents/tasks/{task}/events").json()
        assert len([e for e in journal if e["stage"] == "relevance"]) == 3
        assert len(client.get("/documents/search-profiles").json()["activities"]) == 8
