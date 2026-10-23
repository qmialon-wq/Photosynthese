"""Lightweight SQL operations usable by the HTTP API and document worker."""

from typing import Any

from shared.documents import service
from shared.rag.schemas import Context, DocumentContext, Taxonomy
from shared.review.database import ReviewError, jsonb


def submit(action: str, body: dict[str, Any], actor: str) -> dict[str, Any]:
    return service.submit("rag", {"action": action, "body": body}, actor)


def run(identifier: str) -> dict[str, Any]:
    with service.transaction() as connection:
        row = connection.execute("SELECT * FROM rag_runs WHERE id=%s", (identifier,)).fetchone()
    if not row:
        raise ReviewError("Rapport ou recherche RAG introuvable", 404)
    return row


def video_context(video_id: str, body: Context, actor: str) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    with service.transaction(write=True) as connection:
        if not connection.execute(
            "SELECT 1 FROM review_videos WHERE id=%s", (video_id,)
        ).fetchone():
            raise ReviewError("Vidéo de revue inconnue", 404)
        connection.execute(
            """INSERT INTO rag_video_context(video_id,context,actor) VALUES(%s,%s,%s)
            ON CONFLICT(video_id) DO UPDATE SET context=excluded.context,actor=excluded.actor,
            updated_at=now()""",
            (video_id, jsonb(payload), actor),
        )
        connection.execute(
            "INSERT INTO rag_context_history(video_id,context,actor) VALUES(%s,%s,%s)",
            (video_id, jsonb(payload), actor),
        )
    return {"video_id": video_id, "context": payload, "actor": actor}


def document_context(document_id: str, body: DocumentContext, actor: str) -> dict[str, Any]:
    document_id = str(service.document(document_id)["id"])
    payload = body.model_dump(mode="json")
    with service.transaction(write=True) as connection:
        connection.execute(
            """INSERT INTO rag_document_context(document_id,context,actor) VALUES(%s,%s,%s)
            ON CONFLICT(document_id) DO UPDATE SET context=excluded.context,actor=excluded.actor,
            updated_at=now()""",
            (document_id, jsonb(payload), actor),
        )
        service.event(
            None,
            "rag-context",
            "Contexte documentaire corrigé",
            document=document_id,
            data={"context": payload, "actor": actor},
            connection=connection,
        )
    return payload


def taxonomy(species: str, body: Taxonomy, actor: str) -> dict[str, Any]:
    with service.transaction(write=True) as connection:
        if not connection.execute(
            "SELECT 1 FROM document_species_catalog WHERE name=%s", (species,)
        ).fetchone():
            raise ReviewError("Espèce inconnue", 422)
        row = connection.execute(
            """INSERT INTO rag_taxonomy
            (species,cd_nom,taxref_version,scientific_name,source_url,actor)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(species) DO UPDATE SET
            cd_nom=excluded.cd_nom,taxref_version=excluded.taxref_version,
            scientific_name=excluded.scientific_name,source_url=excluded.source_url,
            actor=excluded.actor,updated_at=now() RETURNING *""",
            (
                species,
                body.cd_nom,
                body.taxref_version,
                body.scientific_name,
                str(body.source_url),
                actor,
            ),
        ).fetchone()
        service.event(
            None,
            "rag-taxonomy",
            "Métadonnées TAXREF fournies explicitement",
            data={"species": species, **body.model_dump(mode="json"), "actor": actor},
            connection=connection,
        )
    return row


def observations(video_ids: list[str], species: list[str]) -> list[dict[str, Any]]:
    if not video_ids:
        return []
    with service.transaction() as connection:
        return connection.execute(
            """SELECT s.id AS sample_id,s.current_revision AS revision,r.label AS species,
            r.state,r.actor AS validator,r.created_at AS validated_at,
            s.classification_score AS original_prediction_score,
            f.video_id,f.frame_index,f.time_seconds,c.context,
            t.cd_nom,t.taxref_version,t.scientific_name,t.source_url AS taxref_source
            FROM review_samples s JOIN review_revisions r
              ON r.sample_id=s.id AND r.revision=s.current_revision
            JOIN review_frames f ON f.id=s.frame_id
            LEFT JOIN rag_video_context c ON c.video_id=f.video_id
            LEFT JOIN rag_taxonomy t ON t.species=r.label
            WHERE r.state IN ('validated','corrected') AND f.video_id=ANY(%s)
            AND (%s OR r.label=ANY(%s)) ORDER BY f.video_id,f.frame_index,s.id""",
            (video_ids, not species, species),
        ).fetchall()
