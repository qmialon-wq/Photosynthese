"""Adaptateurs réels des API publiques ; chaque copie porte sa propre licence."""

import html
import re
from collections.abc import Iterator
from typing import Any, Protocol
from urllib.parse import quote

from shared.documents.relevance import query_groups
from shared.documents.schemas import FullText, Publication, Search, normalize_doi

from .http import SafeHTTP


def clean(value: str | None) -> str | None:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(value or ""))).strip() or None


def license_code(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    if not value.startswith(("http://", "https://")):
        value = re.sub(r"\s+", "-", value)
    if not value:
        return None
    for key in ("cc-by-sa", "cc-by", "cc0"):
        if value == key or value == key.replace("-", ""):
            return key
    match = re.fullmatch(
        r"https?://creativecommons\.org/(?:licenses/(by(?:-sa)?)/[\d.]+|publicdomain/(zero)/[\d.]+)/?",
        value,
    )
    if match:
        return "cc0" if match[2] else "cc-" + match[1]
    return None


def terms(search: Search, *, boolean: bool = False) -> str:
    groups = [search.species, search.habitats, search.territories, search.topics]
    if boolean:
        groups += query_groups(search)
        return " AND ".join(
            "(" + " OR ".join('"' + re.sub(r'["\\]', " ", v) + '"' for v in values) + ")"
            for values in groups
            if values
        )
    natural = " ".join(v for values in groups for v in values)
    if search.focus == "human_activities":
        # Crossref classe une requête textuelle ; le filtre local reste indispensable.
        natural += " " + query_groups(search)[0][0] + " wildlife impact mitigation"
    return natural


def retrieval_limit(query: Search) -> int:
    return min(100, query.limit_per_source * (3 if query.focus == "human_activities" else 1))


class ScientificSource(Protocol):
    name: str

    def search(self, query: Search) -> Iterator[Publication]: ...


class SourceAdapter:
    def __init__(self, http: SafeHTTP) -> None:
        self.http = http
        self.errors = 0

    def parse_items(self, items: list[dict[str, Any]]) -> Iterator[Publication]:
        for item in items:
            try:
                yield self.parse(item)
            except (KeyError, ValueError, TypeError, IndexError, AttributeError) as exc:
                self.errors += 1
                self.http.log(
                    stage="metadata",
                    message=f"Notice malformée : {type(exc).__name__}",
                    level="warning",
                    data={"source": self.name},
                )

    @staticmethod
    def parse(item: dict[str, Any]) -> Publication:
        raise NotImplementedError


class OpenAlex(SourceAdapter):
    name = "openalex"

    def search(self, query: Search) -> Iterator[Publication]:
        result = self.http.json(
            "https://api.openalex.org/works",
            {
                "search": terms(query, boolean=True),
                "per-page": retrieval_limit(query),
            },
        )
        yield from self.parse_items(result.get("results", []))

    @staticmethod
    def parse(item: dict[str, Any]) -> Publication:
        words = {
            p: word
            for word, positions in (item.get("abstract_inverted_index") or {}).items()
            for p in positions
            if isinstance(p, int) and 0 <= p < 100000
        }
        fulltexts = []
        for location in item.get("locations") or []:
            license = license_code(location.get("license"))
            if location.get("is_oa") and location.get("pdf_url") and license:
                fulltexts.append(
                    FullText(
                        url=location["pdf_url"],
                        license=license,
                        evidence=(
                            f"OpenAlex location {location.get('id', '')}: "
                            f"is_oa=true, licence={location.get('license')}"
                        ),
                    )
                )
        return Publication(
            source="openalex",
            source_id=item["id"].rsplit("/", 1)[-1],
            title=clean(item.get("title") or item.get("display_name")) or "Sans titre",
            authors=[
                r["author"]["display_name"]
                for r in item.get("authorships", [])
                if r.get("author", {}).get("display_name")
            ],
            doi=normalize_doi(item.get("doi")),
            published_date=item.get("publication_date"),
            abstract=" ".join(words[p] for p in sorted(words)) or None,
            url=(item.get("primary_location") or {}).get("landing_page_url") or item.get("doi"),
            license=fulltexts[0].license if fulltexts else None,
            fulltexts=fulltexts,
            raw=item,
        )


class Crossref(SourceAdapter):
    name = "crossref"

    def search(self, query: Search) -> Iterator[Publication]:
        params: dict[str, Any] = {"query": terms(query), "rows": retrieval_limit(query)}
        if self.http.settings.contact_email:
            params["mailto"] = self.http.settings.contact_email
        result = self.http.json("https://api.crossref.org/works", params)
        yield from self.parse_items(result.get("message", {}).get("items", []))

    def lookup(self, doi: str) -> Publication:
        data = self.http.json("https://api.crossref.org/works/" + quote(doi, safe=""), {})
        return self.parse(data["message"])

    @staticmethod
    def parse(item: dict[str, Any]) -> Publication:
        parts = (item.get("published", {}).get("date-parts") or [[]])[0]
        return Publication(
            source="crossref",
            source_id=normalize_doi(item["DOI"]) or item["DOI"],
            doi=item["DOI"],
            title=clean((item.get("title") or [""])[0]) or "Sans titre",
            authors=[
                " ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "")
                for a in item.get("author", [])
            ],
            published_date="-".join(str(v) if i == 0 else f"{v:02}" for i, v in enumerate(parts))
            or None,
            abstract=clean(item.get("abstract")),
            url=item.get("URL"),
            license=(item.get("license") or [{}])[0].get("URL"),
            raw=item,
            # Une URL TDM Crossref n'est pas une preuve d'accès ni de licence pour cette copie.
        )


class EuropePMC(SourceAdapter):
    name = "europepmc"

    def search(self, query: Search) -> Iterator[Publication]:
        data = self.http.json(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            {
                "query": terms(query, boolean=True),
                "format": "json",
                "resultType": "core",
                "pageSize": retrieval_limit(query),
            },
        )
        yield from self.parse_items(data.get("resultList", {}).get("result", []))

    @staticmethod
    def parse(item: dict[str, Any]) -> Publication:
        fulltexts = []
        code = license_code(item.get("license"))
        pmcid = item.get("pmcid")
        if item.get("isOpenAccess") == "Y" and code:
            if pmcid and re.fullmatch(r"PMC\d+", pmcid):
                fulltexts.append(
                    FullText(
                        url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                        format="xml",
                        license=code,
                        evidence="Europe PMC core: isOpenAccess=Y et licence explicite",
                    )
                )
            for link in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
                if link.get("availabilityCode") == "OA" and link.get("documentStyle") == "pdf":
                    fulltexts.append(
                        FullText(
                            url=link["url"],
                            license=code,
                            evidence="Europe PMC core: copie PDF OA et licence explicite",
                        )
                    )
        return Publication(
            source="europepmc",
            source_id=f"{item['source']}:{item['id']}",
            title=clean(item.get("title")) or "Sans titre",
            authors=[
                a["fullName"]
                for a in item.get("authorList", {}).get("author", [])
                if a.get("fullName")
            ],
            doi=item.get("doi"),
            published_date=item.get("firstPublicationDate") or item.get("pubYear"),
            abstract=clean(item.get("abstractText")),
            url=f"https://europepmc.org/article/{item['source']}/{item['id']}",
            identifiers={k: item[k] for k in ("pmid", "pmcid") if item.get(k)},
            license=item.get("license"),
            fulltexts=fulltexts,
            raw=item,
        )


SOURCES: dict[str, type[OpenAlex] | type[Crossref] | type[EuropePMC]] = {
    "openalex": OpenAlex,
    "crossref": Crossref,
    "europepmc": EuropePMC,
}
