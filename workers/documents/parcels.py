"""Build the parcel dossier after video inference, using real local evidence only."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shared import console
from shared.documents import service as documents
from shared.parcels import service
from shared.parcels.report import THEMES, planning_questions, suggestions
from shared.parcels.schemas import LAND_TYPES, PROJECT_TYPES
from shared.rag import service as rag_service
from shared.rag.config import RagSettings
from shared.rag.schemas import Filters, Index, Search
from shared.review.database import jsonb
from workers.documents import embeddings, retrieval


def evidence_context(video_id: str, analysis_id: str) -> dict[str, Any]:
    video = console.video(video_id)
    analysis = console.task(analysis_id)
    if analysis["kind"] != "analysis" or analysis["status"] != "completed":
        raise ValueError("L'analyse vidéo doit être terminée")
    if analysis["request"].get("video_id") != video_id:
        raise ValueError("Analyse et vidéo incompatibles")
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/vision").resolve()
    path = (root / analysis["result"]["output"] / "report.json").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Le rapport vidéo d'origine est absent")
    report = json.loads(path.read_text(encoding="utf-8"))
    with documents.transaction() as connection:
        catalog = connection.execute(
            "SELECT * FROM document_species_catalog ORDER BY class_index"
        ).fetchall()
        # An imported console UUID and a human-review video SHA identify the same original file.
        review_ids = connection.execute(
            "SELECT id FROM review_videos WHERE id=ANY(%s)", ([video_id, video["sha256"]],)
        ).fetchall()
    observed = rag_service.observations([r["id"] for r in review_ids], [])
    confirmed = {r["species"] for r in observed}
    canonical = {r["name"]: r for r in catalog}
    predicted: dict[str, float] = {}
    uncertain = unclassified = 0
    for frame in report.get("frames", []):
        for detection in frame.get("detections", []):
            if detection.get("state") == "species_uncertain":
                uncertain += 1
            elif detection.get("state") == "detection_unclassified":
                unclassified += 1
            elif detection.get("state") == "species_recognized":
                classification = detection.get("classification") or {}
                label, score = classification.get("label"), classification.get("score")
                if label in canonical and isinstance(score, int | float) and 0 <= score <= 1:
                    predicted[label] = max(predicted.get(label, 0), float(score))
    return {
        "observations": observed,
        "confirmed_species": [canonical[s] for s in sorted(confirmed)],
        "predicted_species": [
            {**canonical[s], "score": score}
            for s, score in sorted(predicted.items())
            if s not in confirmed
        ],
        "uncertain_detections": uncertain,
        "unclassified_detections": unclassified,
        "analysis_status": report.get("status"),
        "detections": report.get("detections", 0),
        "frames_decoded": report.get("frames_decoded", 0),
        "report_sha256": service.snapshot_sha(report),
    }


def build(identifier: str) -> dict[str, Any]:
    dossier = service.dossier(identifier)
    if dossier["status"] == "completed":
        return {"dossier_id": identifier, "status": "completed"}
    profile = dossier["profile"]
    contexts = [evidence_context(v["video_id"], str(v["analysis_id"])) for v in dossier["videos"]]
    context = aggregate(contexts)
    settings, mode, warning = RagSettings(), "hybrid", None
    try:
        model = embeddings.load(settings)
    except ValueError:
        model, mode = None, "lexical"
        warning = "Recherche lexicale utilisée : modèle multilingue local non préparé."
    if model is not None:
        retrieval.index(Index(), settings, model)
    species = [r["name"] for r in context["confirmed_species"]] or [
        r["name"] for r in context["predicted_species"]
    ]
    target_species = context["confirmed_species"] or context["predicted_species"]
    scientific = " ".join(r["scientific_name"] for r in target_species)
    habitat = {
        "woodland": "woodland forest",
        "pasture": "grassland pasture",
        "fallow": "fallow land",
        "buildable": "building development site",
        "artificial": "urban artificial land",
    }[profile["land_type"]]
    activity = {
        "housing": "housing construction",
        "crops": "agriculture crop farming",
        "livestock": "livestock pasture fencing",
        "park": "park garden recreation",
        "other": "human land use",
    }[profile["project_type"]]
    selected, unique, cards = [], {}, []
    for theme in THEMES:
        # Locality is context, not proof that international literature applies to the parcel.
        request = Search(
            question=f"{theme.query} {scientific} {habitat} {activity}".strip()
            if mode == "hybrid"
            else {
                "vegetation": "hedgerows",
                "connections": "corridors",
                "lighting": "lighting",
                "soil": "impervious",
                "water": "wetlands",
                "timing": "breeding",
            }[theme.key],
            mode=mode,
            filters=Filters(species=species),
            limit=8,
        )
        result = retrieval.retrieve(request, settings, model)
        hits = []
        for hit in result["hits"]:
            if hit["chunk_id"] not in unique:
                unique[hit["chunk_id"]] = {**hit, "citation": f"S{len(unique) + 1}"}
            hits.append(unique[hit["chunk_id"]])
        card = suggestions(theme, hits, bool(context["confirmed_species"]))
        cards.append(card)
        if card.get("citation"):
            selected.append(next(hit for hit in hits if hit["citation"] == card["citation"]))
    sources = list({hit["citation"]: hit for hit in selected}.values())
    has_sources = bool(sources)
    summary = "Aucun animal détecté sur les images analysées. Cela ne démontre pas l'absence "
    summary += "d'animaux sur la parcelle."
    if context["detections"]:
        summary = "Des animaux sont détectés. Les propositions automatiques restent des hypothèses "
        summary += "jusqu'à leur confirmation humaine. Les images répétées "
        summary += "ne dénombrent pas des individus."
    result = {
        "version": "parcel-evidence-v2",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": profile,
        "profile_revision": dossier["profile_revision"],
        "land_label": LAND_TYPES[profile["land_type"]],
        "project_label": PROJECT_TYPES[profile["project_type"]],
        "analysis_id": str(dossier["analysis_id"]),
        "video_id": dossier["video_id"],
        "corpus_id": str(dossier["corpus_id"]) if dossier["corpus_id"] else None,
        "videos": [
            {
                "video_id": v["video_id"],
                "filename": v["filename"],
                "sha256": v["sha256"],
                "analysis_id": str(v["analysis_id"]),
                "annotated_video_url": f"/console/tasks/{v['analysis_id']}/artifacts/video",
                "report_sha256": c["report_sha256"],
                "detections": c["detections"],
                "frames_decoded": c["frames_decoded"],
                "confirmed_species": c["confirmed_species"],
                "predicted_species": c["predicted_species"],
            }
            for v, c in zip(dossier["videos"], contexts, strict=True)
        ],
        "annotated_video_url": f"/console/tasks/{dossier['analysis_id']}/artifacts/video",
        **context,
        "observation_summary": summary,
        "recommendations": cards,
        "sources": sources,
        "status": "sourced_directions" if has_sources else "insufficient_sources",
        "retrieval_mode": mode,
        "embedding_version": model.version if model else None,
        "generation": "conservative-evidence-rules-v1",
        "green_space": {
            "recommended_percent": None,
            "recommended_area_m2": None,
            "message": "Les sources disponibles ne permettent pas de fixer un pourcentage "
            "de terrain vert applicable à cette parcelle. Aucun taux n'est inventé. "
            "Définir cet objectif après examen du site, de ses habitats et du projet.",
        },
        "planning_questions": planning_questions(profile),
        "next_steps": [
            "Confirmer les espèces proposées dans la validation humaine.",
            "Repérer les habitats et éléments existants sur un plan de la parcelle.",
            "Comparer les variantes d'implantation avec l'activité souhaitée.",
            "Actualiser le dossier après les confirmations ou corrections.",
        ],
        "limitations": [
            "Pistes de conception inférées, sans garantie d'efficacité sur ce site.",
            "Ces vidéos ne constituent pas un inventaire complet de la biodiversité.",
            "La localisation déclarée n'établit pas la transférabilité des publications.",
            "Les phrases sources peuvent rester en anglais ; les traductions sont "
            "consultables dans la bibliothèque documentaire.",
        ]
        + ([warning] if warning else []),
    }
    result["snapshot_sha256"] = service.snapshot_sha(
        {"profile": profile, "context": context, "sources": sources}
    )
    result = json.loads(json.dumps(result, default=str, ensure_ascii=False))
    with documents.transaction() as connection:
        connection.execute(
            """UPDATE parcel_dossiers SET status='completed',result=%s,
            error=NULL,finished_at=now() WHERE id=%s""",
            (jsonb(result), identifier),
        )
        documents.event(
            str(dossier["task_id"]),
            "parcel",
            "Dossier de parcelle disponible",
            data={"dossier_id": identifier, "sources": len(sources), "status": result["status"]},
            connection=connection,
        )
    return {"dossier_id": identifier, "status": "completed"}


def aggregate(contexts: list[dict[str, Any]]) -> dict[str, Any]:
    confirmed, predicted, observed = {}, {}, {}
    for context in contexts:
        for row in context["confirmed_species"]:
            confirmed[row["name"]] = row
        for row in context["predicted_species"]:
            if row["score"] > predicted.get(row["name"], {}).get("score", -1):
                predicted[row["name"]] = row
        for row in context["observations"]:
            observed[row["sample_id"]] = row
    return {
        "confirmed_species": [confirmed[k] for k in sorted(confirmed)],
        "predicted_species": [predicted[k] for k in sorted(predicted) if k not in confirmed],
        "observations": list(observed.values()),
        "uncertain_detections": sum(c["uncertain_detections"] for c in contexts),
        "unclassified_detections": sum(c["unclassified_detections"] for c in contexts),
        "detections": sum(c["detections"] for c in contexts),
        "frames_decoded": sum(c["frames_decoded"] for c in contexts),
        "video_count": len(contexts),
        "report_sha256": service.snapshot_sha([c["report_sha256"] for c in contexts]),
    }
