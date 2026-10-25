import httpx
import pytest

from shared.documents.config import DocumentSettings
from shared.documents.schemas import Search, normalize_doi
from workers.documents.http import FetchError, SafeHTTP, public_url
from workers.documents.sources import Crossref, EuropePMC, OpenAlex, license_code


def test_doi_and_source_metadata_preserve_licence_evidence():
    assert normalize_doi("https://doi.org/10.1234/TeSt") == "10.1234/test"
    article = OpenAlex.parse(
        {
            "id": "https://openalex.org/W1",
            "title": "Synthetic fixture",
            "doi": "https://doi.org/10.1234/test",
            "abstract_inverted_index": {"woodland": [1], "Fox": [0]},
            "locations": [
                {"is_oa": True, "pdf_url": "https://example.org/a.pdf", "license": "cc-by"},
                {"is_oa": True, "pdf_url": "https://example.org/b.pdf", "license": None},
            ],
        }
    )
    assert article.abstract == "Fox woodland" and len(article.fulltexts) == 1
    assert article.fulltexts[0].license == "cc-by"
    crossref = Crossref.parse(
        {
            "DOI": "10.1234/TEST",
            "title": ["Fixture"],
            "published": {"date-parts": [[2024]]},
            "link": [{"URL": "https://publisher.test/paywall.pdf"}],
        }
    )
    assert crossref.doi == article.doi and not crossref.fulltexts
    europe = EuropePMC.parse(
        {
            "source": "MED",
            "id": "1",
            "pmcid": "PMC123",
            "isOpenAccess": "Y",
            "title": "Fixture",
            "license": "ccby",
        }
    )
    assert europe.fulltexts[0].format == "xml" and europe.identifiers["pmcid"] == "PMC123"
    assert license_code("https://creativecommons.org/licenses/by/4.0/") == "cc-by"
    assert license_code("cc by") == "cc-by"
    assert license_code("cc-by-nc") is None and license_code("other-oa") is None


def test_http_cache_retry_and_no_credentials_forwarded(tmp_path):
    calls, sleeps, headers = [], [], []

    def transport(request):
        calls.append(str(request.url))
        headers.append(request.headers.get("authorization"))
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        if len(calls) == 2:
            return httpx.Response(302, headers={"Location": "https://public.example/data"})
        return httpx.Response(200, json={"results": []})

    settings = DocumentSettings(root=tmp_path, openalex_api_key="test-secret", request_interval=0.2)
    http = SafeHTTP(
        settings,
        client=httpx.Client(transport=httpx.MockTransport(transport)),
        validate=lambda _: None,
        sleep=sleeps.append,
    )
    assert http.json("https://api.openalex.org/works", {}) == {"results": []}
    assert headers == ["Bearer test-secret", "Bearer test-secret", None]
    assert http.json("https://api.openalex.org/works", {}) == {"results": []} and len(calls) == 3
    assert any(delay > 0 for delay in sleeps)
    assert not any("test-secret" in p.read_text(errors="ignore") for p in tmp_path.rglob("*.json"))


def test_private_destinations_and_redirects_are_rejected(tmp_path, monkeypatch):
    import socket

    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))]
    )
    with pytest.raises(FetchError, match="privée"):
        public_url("http://127.0.0.1/internal")
    http = SafeHTTP(
        DocumentSettings(root=tmp_path),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(302, headers={"Location": "http://127.0.0.1/"})
            )
        ),
        validate=lambda url: public_url(url) if "127.0.0.1" in url else None,
        sleep=lambda _: None,
    )
    with pytest.raises(FetchError, match="privée"):
        http.get("https://public.example/file", cache=False)


def test_oversized_responses_fail_without_saving_a_document(tmp_path):
    http = SafeHTTP(
        DocumentSettings(root=tmp_path),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 100))
        ),
        validate=lambda _: None,
        sleep=lambda _: None,
    )
    with pytest.raises(FetchError, match="volumineuse"):
        http.get("https://public.example/file", max_bytes=10)
    assert not list(tmp_path.rglob("*.body"))


def test_malformed_notice_does_not_drop_the_following_notice(tmp_path):
    http = SafeHTTP(
        DocumentSettings(root=tmp_path),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "results": [
                            {"id": "bad", "doi": "invalid"},
                            {"id": "W2", "title": "Fixture"},
                        ]
                    },
                )
            )
        ),
        validate=lambda _: None,
        sleep=lambda _: None,
    )
    source = OpenAlex(http)
    publications = list(source.search(Search(species=["Vulpes vulpes"], sources=["openalex"])))
    assert [p.source_id for p in publications] == ["W2"] and source.errors == 1


@pytest.mark.parametrize("source_class", [OpenAlex, EuropePMC])
def test_paginated_discovery_is_lazy_and_bounded(source_class):
    class HTTP:
        def __init__(self):
            self.calls = []

        def json(self, url, params):
            self.calls.append(params)
            number = len(self.calls)
            if source_class is OpenAlex:
                assert params["page"] == number
                return {"results": [{"id": f"W{number}", "title": "Fixture"}]}
            assert params["cursorMark"] == ("*" if number == 1 else "next-1")
            return {
                "resultList": {"result": [{"source": "MED", "id": str(number)}]},
                "nextCursorMark": f"next-{number}",
            }

    http = HTTP()
    iterator = source_class(http).search(
        Search(species=["Vulpes vulpes"], limit_per_source=1, max_pages=2)
    )
    assert http.calls == []
    next(iterator)
    assert len(http.calls) == 1
    assert len(list(iterator)) == 1
    assert len(http.calls) == 2


def test_europepmc_stops_on_repeated_cursor():
    class HTTP:
        def json(self, url, params):
            return {
                "resultList": {"result": [{"source": "MED", "id": "1"}]},
                "nextCursorMark": "*",
            }

    assert len(list(EuropePMC(HTTP()).search(Search(species=["Vulpes vulpes"], max_pages=10)))) == 1
