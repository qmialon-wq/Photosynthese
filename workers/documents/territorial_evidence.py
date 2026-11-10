"""Optional local lexical evidence, no encoder, model download or LLM generation."""

from datetime import UTC, datetime
from uuid import uuid4

from shared.parcels.territorial_rules import analyze
from shared.parcels.territorial_schemas import Analysis
from shared.rag.config import RagSettings
from shared.rag.schemas import Filters, Search
from shared.review.database import jsonb, transaction
from workers.documents import retrieval

TERMS = {
    "fencing": ("fencing", "fence"),
    "outdoor_lighting": ("lighting", "light"),
    "vegetation_removal": ("hedgerows", "vegetation"),
    "earthworks": ("construction", "soil"),
    "soil_sealing": ("impervious", "sealing"),
}


def candidates(inputs: dict) -> list[dict]:
    species = sorted(
        {
            r["species"]
            for r in inputs.get("observations", [])
            if r.get("state") in ("validated", "corrected")
        }
    )
    if not species:
        return []
    found = {}
    # At most ten local queries, four excerpts each, no remote or model operations.
    for code in inputs.get("profile", {}).get("interventions", []):
        for term in TERMS.get(code, ()):
            result = retrieval.retrieve(
                Search(question=term, mode="lexical", filters=Filters(species=species), limit=4),
                RagSettings(),
                model=None,
            )
            for hit in result["hits"]:
                key = (hit["chunk_id"], code)
                found[key] = {
                    "id": f"doc:{hit['chunk_id']}:{code}",
                    "title": hit["title"],
                    "url": hit.get("source_url"),
                    "original_url": hit["original_url"],
                    "document_id": hit["document_id"],
                    "chunk_id": hit["chunk_id"],
                    "text": hit["text"],
                    "page": hit["page"],
                    "page_kind": hit["page_kind"],
                    "sha256": hit["asset_sha256"],
                    "text_sha256": hit["text_sha256"],
                    "provenance": hit["provenance"],
                    "project_action": code,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "relevance_reason": f"Correspondance lexicale « {term} » ; corpus admissible "
                    f"lié aux espèces validées : {', '.join(species)}.",
                    "applicability": "not_assessed",
                    "limitation": "Correspondance lexicale uniquement ; ne justifie aucune mesure.",
                }
    return list(found.values())


def enrich(identifier: str) -> dict:
    with transaction() as c:
        row = c.execute("SELECT * FROM territorial_queries WHERE id=%s", (identifier,)).fetchone()
        existing = c.execute(
            "SELECT id FROM territorial_queries WHERE result->'documentary'->>'base_query_id'=%s",
            (identifier,),
        ).fetchone()
    if existing:
        return {"status": "candidates_archived", "query_id": str(existing["id"])}
    if not row or not row["result"]:
        raise ValueError("Résultat déterministe préalable absent")
    sources = candidates(row["inputs"])
    if not sources:
        return {"status": "no_sources", "message": "Aucun extrait admissible pertinent disponible."}
    with transaction(write=True) as c:
        # Serialize revision allocation with the location/profile/consultation writes.
        existing = c.execute(
            "SELECT id FROM territorial_queries WHERE result->'documentary'->>'base_query_id'=%s",
            (identifier,),
        ).fetchone()
        if existing:
            return {"status": "candidates_archived", "query_id": str(existing["id"])}
        latest = c.execute(
            "SELECT id,revision FROM territorial_queries WHERE corpus_id=%s "
            "ORDER BY revision DESC LIMIT 1",
            (row["corpus_id"],),
        ).fetchone()
        if str(latest["id"]) != identifier:
            return {"status": "superseded", "message": "Une consultation plus récente existe."}
        revision = latest["revision"] + 1
        result = analyze(row["inputs"], row["layers"], revision)
        result["sources"].extend(sources)
        result["documentary"] = {
            "status": "candidates_only",
            "base_query_id": identifier,
            "method": "bounded_local_lexical",
            "excerpt_count": len(sources),
        }
        result["unknowns"].append(
            "Extraits complémentaires à examiner : leur applicabilité "
            "locale et leur soutien à une mesure ne sont pas établis."
        )
        result = Analysis.model_validate(result).model_dump()
        new_id = str(uuid4())
        c.execute(
            "INSERT INTO territorial_queries "
            "(id,corpus_id,revision,input_sha256,inputs,layers,result,actor,finished_at) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,now())",
            (
                new_id,
                row["corpus_id"],
                revision,
                row["input_sha256"],
                jsonb(row["inputs"]),
                jsonb(row["layers"]),
                jsonb(result),
                row["actor"],
            ),
        )
    return {"status": "candidates_archived", "query_id": new_id, "excerpt_count": len(sources)}
