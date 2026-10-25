"""Objectif de corpus distinct, avec passages urbain et agricole prioritaires."""

from typing import TYPE_CHECKING, Any

from shared.documents.corpus import listing
from shared.documents.schemas import Search

if TYPE_CHECKING:
    from .ingestion import Ingestor


def run(ingestor: "Ingestor", request: dict[str, Any]) -> dict[str, Any]:
    target = min(100, max(1, int(request["collection_target"])))
    species = request["collection_species"]
    existing = listing(species, False, None, False, 10000, 0, stored_only=True)
    stored = {str(row["id"]) for row in existing}
    initial = len(stored)
    counts = dict.fromkeys(
        ("observed", "errors", "sources_ok", "inaccessible", "filtered_out", "downloaded"), 0
    )
    documents: set[str] = set()
    downloaded: set[str] = set()
    passes = []
    # Les quotas sont souples : le passage général complète si un milieu est peu documenté.
    for activity, quota in (("urban", 25), ("agriculture", 25), ("all", target)):
        remaining = target - len(stored)
        if remaining <= 0:
            break
        query = Search.model_validate(request["search"]).model_copy(
            update={"activity": activity, "limit_per_source": min(quota, remaining)}
        )
        result = ingestor.search(
            {**request, "collection_target": None, "search": query.model_dump()},
            stored=stored,
            total_limit=min(quota, remaining),
        )
        for key in counts:
            counts[key] += result[key]
        documents.update(result["document_ids"])
        downloaded.update(result["downloaded_ids"])
        passes.append({"activity": activity, "downloaded": result["downloaded"]})
        ingestor.log(
            "collection",
            "Passage de collecte terminé",
            data={"activity": activity, "stored": len(stored), "target": target},
        )
    return {
        **counts,
        "document_ids": sorted(documents),
        "downloaded_ids": sorted(downloaded),
        "target": target,
        "initial_count": initial,
        "corpus_count": len(stored),
        "target_reached": len(stored) >= target,
        "passes": passes,
    }
