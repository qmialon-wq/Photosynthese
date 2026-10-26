"""Persist questionnaire revisions and schedule dossiers independently of an open browser."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from shared import console
from shared.documents import service as documents
from shared.parcels.schemas import Profile
from shared.review.database import ReviewError, jsonb, transaction


def options() -> dict[str, Any]:
    from .schemas import LAND_TYPES, PROJECT_TYPES

    return {"land_types": LAND_TYPES, "project_types": PROJECT_TYPES}


def profile(video_id: str) -> dict[str, Any] | None:
    with transaction() as connection:
        return connection.execute(
            "SELECT * FROM parcel_profiles WHERE video_id=%s ORDER BY revision DESC LIMIT 1",
            (video_id,),
        ).fetchone()


def save(video_id: str, body: Profile, actor: str) -> dict[str, Any]:
    console.video(video_id)
    data = body.model_dump(exclude={"expected_revision"})
    with transaction(write=True) as connection:
        previous = connection.execute(
            "SELECT * FROM parcel_profiles WHERE video_id=%s ORDER BY revision DESC LIMIT 1",
            (video_id,),
        ).fetchone()
        revision = previous["revision"] if previous else 0
        if revision != body.expected_revision:
            raise ReviewError("La parcelle a été modifiée ailleurs. Rechargez le formulaire.", 409)
        if previous and previous["profile"] == data:
            return previous
        return connection.execute(
            """INSERT INTO parcel_profiles(video_id,revision,profile,actor) VALUES(%s,%s,%s,%s)
            RETURNING *""",
            (video_id, revision + 1, jsonb(data), actor),
        ).fetchone()


def request(
    video_id: str,
    analysis_id: str,
    revision: int,
    actor: str,
    connection: Any = None,
) -> dict[str, Any]:
    if connection is None:
        with transaction(write=True) as current:
            return request(video_id, analysis_id, revision, actor, current)
    if not connection.execute(
        "SELECT 1 FROM parcel_profiles WHERE video_id=%s AND revision=%s", (video_id, revision)
    ).fetchone():
        raise ReviewError("Formulaire de parcelle absent ou version inconnue", 422)
    analysis = connection.execute(
        "SELECT * FROM console_tasks WHERE id=%s", (analysis_id,)
    ).fetchone()
    if (
        not analysis
        or analysis["kind"] != "analysis"
        or analysis["request"].get("video_id") != video_id
    ):
        raise ReviewError("Cette analyse n'appartient pas à la vidéo", 422)
    if analysis["status"] in ("error", "cancelled"):
        raise ReviewError("Relancez d'abord l'analyse vidéo", 409)
    # Reuse a pending dossier; a completed one can be refreshed after validation.
    active = connection.execute(
        """SELECT * FROM parcel_dossiers WHERE video_id=%s AND analysis_id=%s
        AND profile_revision=%s AND status IN ('waiting_analysis','queued')
        AND NOT EXISTS(SELECT 1 FROM document_tasks t WHERE t.id=parcel_dossiers.task_id
                       AND t.status IN ('error','partial','completed')) LIMIT 1""",
        (video_id, analysis_id, revision),
    ).fetchone()
    if active:
        return active
    return connection.execute(
        """INSERT INTO parcel_dossiers(id,video_id,analysis_id,profile_revision,actor)
        VALUES(%s,%s,%s,%s,%s) RETURNING *""",
        (str(uuid4()), video_id, analysis_id, revision, actor),
    ).fetchone()


def schedule() -> int:
    """Called by the document worker heartbeat; SQL only, no inference here."""
    with documents.transaction(write=True) as connection:
        rows = connection.execute("""SELECT d.*,t.status AS analysis_status FROM parcel_dossiers d
            JOIN console_tasks t ON t.id=d.analysis_id WHERE d.status='waiting_analysis'
            ORDER BY d.created_at FOR UPDATE OF d SKIP LOCKED LIMIT 50""").fetchall()
        queued = 0
        for row in rows:
            entries = inputs(connection, row)
            if any(entry["analysis_status"] in ("cancelled", "error") for entry in entries):
                connection.execute(
                    """UPDATE parcel_dossiers SET status='error',
                    error='Une analyse du dossier est interrompue ou en erreur. '
                          'Aucune vidéo ne sera écartée silencieusement.',finished_at=now()
                    WHERE id=%s""",
                    (row["id"],),
                )
            elif all(entry["analysis_status"] == "completed" for entry in entries):
                task = documents.submit(
                    "rag",
                    {"action": "parcel", "body": {"dossier_id": str(row["id"])}},
                    row["actor"],
                    dedup_key=f"parcel:{row['id']}",
                    connection=connection,
                )
                connection.execute(
                    "UPDATE parcel_dossiers SET status='queued',task_id=%s WHERE id=%s",
                    (task["id"], row["id"]),
                )
                queued += 1
        return queued


def inputs(connection: Any, row: dict[str, Any]) -> list[dict[str, Any]]:
    entries = connection.execute(
        """SELECT v.*,t.status AS analysis_status,t.error AS analysis_error
        FROM parcel_dossier_videos v JOIN console_tasks t ON t.id=v.analysis_id
        WHERE v.dossier_id=%s ORDER BY v.ordinal""",
        (row["id"],),
    ).fetchall()
    if entries:
        return entries
    video = console.video(row["video_id"])
    task = console.task(str(row["analysis_id"]))
    return [
        {
            "video_id": row["video_id"],
            "filename": video["filename"],
            "sha256": video["sha256"],
            "analysis_id": row["analysis_id"],
            "analysis_status": task["status"],
            "analysis_error": task["error"],
        }
    ]


def dossier(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            """SELECT d.*,coalesce(p.profile,c.profile) AS profile,
            t.status AS task_status,t.error AS task_error
            FROM parcel_dossiers d LEFT JOIN parcel_profiles p
            ON p.video_id=d.video_id AND p.revision=d.profile_revision
            LEFT JOIN parcel_corpus_profiles c
            ON c.corpus_id=d.corpus_id AND c.revision=d.profile_revision
            LEFT JOIN document_tasks t ON t.id=d.task_id WHERE d.id=%s""",
            (identifier,),
        ).fetchone()
        if row:
            row["videos"] = inputs(connection, row)
            from .progress import read as read_progress

            row["progress"] = read_progress(connection, row["task_id"])
            row["video_count"] = len(row["videos"])
            row["completed_video_count"] = sum(
                v["analysis_status"] == "completed" for v in row["videos"]
            )
    if not row:
        raise ReviewError("Dossier introuvable", 404)
    if row["task_status"] == "error" and row["status"] != "completed":
        row["status"], row["error"] = "error", row["task_error"]
    elif row["task_status"] == "running" and row["status"] == "queued":
        row["status"] = "running"
    return row


def state(video_id: str, analysis_id: str | None = None) -> dict[str, Any]:
    console.video(video_id)
    with transaction() as connection:
        latest = connection.execute(
            """SELECT id FROM parcel_dossiers WHERE video_id=%s
            AND (%s::uuid IS NULL OR analysis_id=%s) ORDER BY created_at DESC LIMIT 1""",
            (video_id, analysis_id, analysis_id),
        ).fetchone()
    return {"profile": profile(video_id), "dossier": dossier(str(latest["id"])) if latest else None}


def snapshot_sha(data: Any) -> str:
    portable = json.loads(json.dumps(data, ensure_ascii=False, default=str))
    return hashlib.sha256(documents.canonical(portable)).hexdigest()
