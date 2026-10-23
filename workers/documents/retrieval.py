"""Hybrid retrieval from currently approved sources; exact pgvector search for local corpora."""

import hashlib
import json
import math
import re
import time
from typing import Any

from shared.documents import service
from shared.documents.corpus import READY
from shared.rag.config import RagSettings
from shared.rag.schemas import Index, Search
from shared.review.database import jsonb
from workers.documents.embeddings import Encoder, load


def vector_literal(values: list[float]) -> str:
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError("Vecteur vide ou non fini")
    return json.dumps(values)


def approved_sql() -> str:
    return f"""{READY} AND d.merged_into IS NULL AND NOT c.is_reference
      AND EXISTS(SELECT 1 FROM document_species s WHERE s.document_id=d.id
                 AND s.enabled AND NOT s.excluded)"""


def index(body: Index, settings: RagSettings, model: Encoder | None = None) -> dict[str, Any]:
    model = model or load(settings)
    with service.transaction() as connection:
        connection.execute(
            "INSERT INTO rag_embedding_versions(id,manifest) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (model.version, jsonb(model.manifest)),
        )
        chunks = connection.execute(
            f"""SELECT c.id,c.text,e.text_sha256 FROM document_chunks c
            JOIN document_assets a ON a.id=c.asset_id
            JOIN scientific_documents d ON d.id=a.document_id
            LEFT JOIN rag_embeddings e ON e.chunk_id=c.id AND e.version=%s
            WHERE {approved_sql()} AND (%s OR d.id=ANY(%s::uuid[])) ORDER BY c.id""",
            (model.version, not body.document_ids, [str(i) for i in body.document_ids]),
        ).fetchall()
    inserted = 0
    for chunk in chunks:
        digest = hashlib.sha256(chunk["text"].encode()).hexdigest()
        if digest == chunk["text_sha256"]:
            continue
        vector = model.encode(chunk["text"])
        if len(vector) != model.manifest["dimension"]:
            raise ValueError("Dimension d'embedding incompatible")
        with service.transaction() as connection:
            connection.execute(
                """INSERT INTO rag_embeddings(chunk_id,version,text_sha256,embedding)
                VALUES(%s,%s,%s,%s::vector) ON CONFLICT(chunk_id,version) DO UPDATE SET
                text_sha256=excluded.text_sha256,embedding=excluded.embedding,created_at=now()""",
                (chunk["id"], model.version, digest, vector_literal(vector)),
            )
        inserted += 1
    return {
        "version": model.version,
        "eligible_chunks": len(chunks),
        "embedded": inserted,
        "cached": len(chunks) - inserted,
    }


def retrieve(body: Search, settings: RagSettings, model: Encoder | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    filters = body.filters
    model_version, query_vector = None, None
    if body.mode == "hybrid":
        model = model or load(settings)
        model_version = model.version
        query_vector = vector_literal(model.encode(body.question, query=True))
    # All filters are bound values; missing territorial metadata never means "local".
    params: list[Any] = [
        not filters.species,
        filters.species,
        filters.habitat,
        filters.habitat,
        filters.territory,
        filters.territory,
        not filters.sources,
        filters.sources,
        str(filters.published_after) if filters.published_after else None,
        str(filters.published_after) if filters.published_after else None,
        str(filters.published_before) if filters.published_before else None,
        str(filters.published_before) if filters.published_before else None,
    ]
    eligibility = f"""SELECT c.*,d.id AS document_id,d.title,d.doi,d.authors,d.published_date,
        a.source_url,a.license,a.sha256 AS asset_sha256,d.url,a.format,
        (SELECT coalesce(jsonb_agg(jsonb_build_object('source',p.source,'source_id',p.source_id,
          'snapshot_sha256',p.snapshot_sha256)), '[]'::jsonb)
          FROM document_provenance p WHERE p.document_id=d.id) AS provenance
        FROM document_chunks c JOIN document_assets a ON a.id=c.asset_id
        JOIN scientific_documents d ON d.id=a.document_id
        LEFT JOIN rag_document_context ctx ON ctx.document_id=d.id
        WHERE {approved_sql()}
        AND (%s OR EXISTS(SELECT 1 FROM document_species s WHERE s.document_id=d.id
          AND s.species=ANY(%s) AND s.enabled AND NOT s.excluded))
        AND (%s::text IS NULL OR ctx.context->'habitats' ? %s)
        AND (%s::text IS NULL OR ctx.context->'territories' ? %s)
        AND (%s OR EXISTS(SELECT 1 FROM document_provenance p
          WHERE p.document_id=d.id AND p.source=ANY(%s)))
        AND (%s::text IS NULL OR (d.published_date ~ '^\u005cd{{4}}-\u005cd{{2}}-\u005cd{{2}}$'
             AND d.published_date>=%s))
        AND (%s::text IS NULL OR (d.published_date ~ '^\u005cd{{4}}-\u005cd{{2}}-\u005cd{{2}}$'
             AND d.published_date<=%s))"""
    # lexical ranking has no arbitrary pre-limit; filter first, rank in PostgreSQL.
    with service.transaction() as connection:
        lexical = connection.execute(
            f"""WITH eligible AS ({eligibility}) SELECT *,ts_rank_cd(search_vector,
            plainto_tsquery('simple',%s)) AS lexical_score FROM eligible
            WHERE search_vector @@ plainto_tsquery('simple',%s)
            ORDER BY lexical_score DESC,id LIMIT 100""",
            [*params, body.question, body.question],
        ).fetchall()
        semantic = []
        if query_vector:
            semantic = connection.execute(
                f"""WITH eligible AS ({eligibility}) SELECT c.*,
                1-(e.embedding <=> %s::vector) AS similarity
                FROM eligible c JOIN rag_embeddings e ON e.chunk_id=c.id
                WHERE e.version=%s AND e.text_sha256=encode(sha256(convert_to(c.text,'UTF8')),'hex')
                AND 1-(e.embedding <=> %s::vector)>=%s
                ORDER BY e.embedding <=> %s::vector,c.id LIMIT 100""",
                [
                    *params,
                    query_vector,
                    model_version,
                    query_vector,
                    settings.min_similarity,
                    query_vector,
                ],
            ).fetchall()
    pool: dict[str, dict[str, Any]] = {}
    semantic_ids = {r["id"] for r in semantic}
    for name, rows in (("lexical", lexical), ("vector", semantic)):
        for rank, row in enumerate(rows, 1):
            if body.mode == "hybrid" and row["id"] not in semantic_ids:
                continue  # Similarity threshold also guards coincidental keyword matches.
            item = pool.setdefault(row["id"], {**row, "score": 0.0, "channels": []})
            item["score"] += 1 / (60 + rank)
            item["channels"].append(name)
            if "similarity" in row:
                item["similarity"] = row["similarity"]
    ranked = sorted(pool.values(), key=lambda r: (-r["score"], r["id"]))
    if body.rerank:
        # Optional deterministic lexical coverage reranker, explicitly not a cross-encoder.
        terms = set(re.findall(r"\w+", body.question.lower()))
        ranked.sort(
            key=lambda r: (
                -len(terms & set(re.findall(r"\w+", r["text"].lower()))) / max(1, len(terms)),
                -r["score"],
                r["id"],
            )
        )
    hits, seen = [], set()
    for row in ranked:
        fingerprint = hashlib.sha256(row["text"].strip().encode()).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        identifier = str(row["document_id"])
        asset = str(row["asset_id"])
        hits.append(
            {
                "citation": f"S{len(hits) + 1}",
                "chunk_id": row["id"],
                "document_id": identifier,
                "asset_id": asset,
                "title": row["title"],
                "authors": row["authors"],
                "doi": row["doi"],
                "published_date": row["published_date"],
                "page": row["page_number"],
                "page_kind": "pdf_page" if row["format"] == "pdf" else "extraction_page",
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "text": row["text"],
                "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
                "language": row["language"],
                "license": row["license"],
                "provenance": row["provenance"],
                "source_url": row["source_url"] or row["url"],
                "asset_sha256": row["asset_sha256"],
                "original_url": f"/documents/{identifier}/assets/{asset}?inline=true",
                "score": row["score"],
                "similarity": row.get("similarity"),
                "channels": row["channels"],
            }
        )
        if len(hits) >= body.limit:
            break
    return {
        "status": "sources_found" if hits else "no_sources",
        "question": body.question,
        "mode": body.mode,
        "embedding_version": model_version,
        "filters": filters.model_dump(mode="json"),
        "reranker": "lexical-coverage-v1" if body.rerank else None,
        "min_similarity": settings.min_similarity if model_version else None,
        "hits": hits,
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "message": "Extraits documentaires à examiner ; pertinence locale non démontrée."
        if hits
        else "Aucune source validée suffisamment pertinente. Aucune recommandation spécifique.",
    }
