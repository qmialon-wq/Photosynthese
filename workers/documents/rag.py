"""Asynchronous RAG stage 1: retrieval, verbatim evidence and evaluation, without a generator."""

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from shared.documents import service
from shared.rag import service as rag_service
from shared.rag.config import RagSettings
from shared.rag.schemas import Evaluation, Index, Report, Search
from shared.review.database import jsonb
from workers.documents import embeddings, retrieval


def report(body: Report, result: dict[str, Any]) -> dict[str, Any]:
    observed = rag_service.observations(body.video_ids, body.filters.species)
    observed_species = {o["species"] for o in observed}
    evidence = [
        {
            "kind": "publication_excerpt",
            "citation": hit["citation"],
            "text": hit["text"],
            "chunk_id": hit["chunk_id"],
        }
        for hit in result["hits"]
    ]
    return {
        **result,
        "generation_enabled": False,
        "report_version": "extractive-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "observed_facts": observed,
        "publication_evidence": evidence,
        "inferred_recommendations": [],
        "recommendation_status": "requires_ecological_interpretation" if evidence else "abstained",
        "cautions": [
            "Les extraits ne sont pas une synthèse des conclusions complètes des publications.",
            "Aucune recommandation écologique spécifique n'est générée dans cette étape sans LLM.",
            "Des annotations ou images répétées ne constituent pas un décompte d'individus.",
            "Les dates de publication ne sont pas la période d'observation.",
            "La transférabilité des études au site normand reste à vérifier.",
        ]
        + (
            ["Aucune observation humaine validée pour les vidéos et espèces demandées."]
            if not observed
            else []
        )
        + (
            [
                "Espèce ciblée sans observation validée : "
                + ", ".join(sorted(set(body.filters.species) - observed_species))
            ]
            if set(body.filters.species) - observed_species
            else []
        ),
        "next_steps": [
            {
                "kind": "methodological",
                "text": "Examiner les résultats, limites et conditions "
                "d'application de ces sources avant toute décision d'aménagement.",
                "citations": [h["citation"] for h in result["hits"]],
            }
        ]
        if evidence
        else [],
    }


def fidelity(result: dict[str, Any]) -> dict[str, Any]:
    hits = {h["citation"]: h for h in result["hits"]}
    evidence = result.get("publication_evidence", [])
    valid = sum(
        e["citation"] in hits
        and e["text"] == hits[e["citation"]]["text"]
        and e["chunk_id"] == hits[e["citation"]]["chunk_id"]
        for e in evidence
    )
    return {
        "verbatim_citation_precision": valid / len(evidence) if evidence else None,
        "cited_excerpts": len(evidence),
        "invalid_citations": len(evidence) - valid,
        "scope": "Exactitude des citations et extraits ; pas de mesure d'entailment écologique.",
    }


def evaluate(body: Evaluation, settings: RagSettings) -> dict[str, Any]:
    cases = []
    for case in body.cases:
        result = retrieval.retrieve(case.search, settings)
        actual = [h["chunk_id"] for h in result["hits"]]
        expected = set(case.relevant_chunks)
        binary = [int(identifier in expected) for identifier in actual]
        dcg = sum(value / math.log2(i + 2) for i, value in enumerate(binary))
        ideal = sum(1 / math.log2(i + 2) for i in range(min(len(expected), case.search.limit)))
        extracted = report(Report(**case.search.model_dump()), result)
        cases.append(
            {
                "question": case.search.question,
                "retrieved": actual,
                "recall_at_k": len(set(actual) & expected) / len(expected),
                "precision_at_k": sum(binary) / case.search.limit,
                "mrr": next((1 / (i + 1) for i, value in enumerate(binary) if value), 0),
                "ndcg": dcg / ideal if ideal else 0,
                "fidelity": fidelity(extracted),
            }
        )
    return {
        "cases": cases,
        "dataset_sha256": hashlib.sha256(
            service.canonical(body.model_dump(mode="json"))
        ).hexdigest(),
        "metrics": {
            key: sum(c[key] for c in cases) / len(cases)
            for key in ("recall_at_k", "precision_at_k", "mrr", "ndcg")
        },
    }


def perform(action: str, body: dict[str, Any], actor: str, task: str, http: Any) -> dict[str, Any]:
    if action == "parcel":
        from workers.documents.parcels import build

        return build(body["dossier_id"])
    with service.transaction() as connection:
        existing = connection.execute(
            "SELECT id,result FROM rag_runs WHERE task_id=%s", (task,)
        ).fetchone()
    if existing:
        return {
            "run_id": str(existing["id"]),
            "result_url": f"/rag/runs/{existing['id']}",
            "status": existing["result"].get("status", "completed"),
        }
    settings = RagSettings()
    if action == "prepare":
        result = embeddings.prepare(settings, http)
    elif action == "index":
        result = retrieval.index(Index.model_validate(body), settings)
    elif action in ("search", "report"):
        request = Report.model_validate(body) if action == "report" else Search.model_validate(body)
        result = retrieval.retrieve(request, settings)
        if action == "report":
            result = report(request, result)
            result["fidelity"] = fidelity(result)
    elif action == "evaluate":
        result = evaluate(Evaluation.model_validate(body), settings)
    else:
        raise ValueError("Action RAG inconnue")
    identifier = str(uuid4())
    # JSON-compatible dates/UUIDs for durable source and observation snapshots.
    result = json.loads(json.dumps(result, default=str, ensure_ascii=False))
    with service.transaction() as connection:
        connection.execute(
            """INSERT INTO rag_runs(id,task_id,kind,request,result,actor)
            VALUES(%s,%s,%s,%s,%s,%s)""",
            (identifier, task, action, jsonb(body), jsonb(result), actor),
        )
        service.event(
            task,
            "rag",
            "Passage RAG terminé",
            data={"run_id": identifier, "action": action, "status": result.get("status")},
            connection=connection,
        )
    return {
        "run_id": identifier,
        "result_url": f"/rag/runs/{identifier}",
        "status": result.get("status", "completed"),
    }
