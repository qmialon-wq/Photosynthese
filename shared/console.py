"""État durable de la console ; aucun import ML ni appel réseau à l'import."""

from typing import Any
from uuid import uuid4

from .review.database import ReviewError, jsonb, transaction

VIDEO_QUERY = """SELECT id,filename,video_key,sha256,species_candidate,metadata,created_at,
 'ready'::text AS status FROM console_videos
 UNION ALL SELECT v.id,v.original_name,v.source_key,v.id,v.species_candidate,
 v.diagnostics,v.created_at,v.status FROM review_videos v
 WHERE NOT EXISTS(SELECT 1 FROM console_videos c WHERE c.sha256=v.id)"""


def activate_model(identifier: str) -> dict[str, Any]:
    with transaction(write=True) as connection:
        row = connection.execute(
            "SELECT id FROM console_models WHERE id=%s", (identifier,)
        ).fetchone()
        if row is None:
            raise ReviewError("Modèle inconnu", 404)
        previous = connection.execute("SELECT id FROM console_models WHERE active").fetchall()
        connection.execute("UPDATE console_models SET active=false WHERE active")
        connection.execute("UPDATE console_models SET active=true WHERE id=%s", (identifier,))
    return {
        "id": identifier,
        "active": True,
        "previous_model_ids": [str(item["id"]) for item in previous],
    }


def video(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM (" + VIDEO_QUERY + ") videos WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Vidéo inconnue", 404)
    return row


def submit(
    kind: str, payload: dict[str, Any], actor: str, connection: Any = None
) -> dict[str, Any]:
    if connection is None:
        with transaction(write=True) as current:
            return submit(kind, payload, actor, current)
    identifier = str(uuid4())
    connection.execute(
        "INSERT INTO console_tasks(id,kind,actor,request) VALUES(%s,%s,%s,%s)",
        (identifier, kind, actor, jsonb(payload)),
    )
    log(connection, identifier, "Tâche soumise à la file locale")
    return {"id": identifier, "status": "queued", "status_url": f"/console/tasks/{identifier}"}


def log(connection: Any, identifier: str, message: str) -> None:
    connection.execute(
        "INSERT INTO console_logs(task_id,message) VALUES(%s,%s)", (identifier, message[:4000])
    )


def task(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM console_tasks WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Tâche inconnue", 404)
    return row


def publish_pending(client: Any) -> int:
    from .vision_jobs import ConsoleRequest, JobStore

    with transaction() as connection:
        rows = connection.execute(
            "SELECT id FROM console_tasks WHERE published_at IS NULL AND status='queued' "
            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20"
        ).fetchall()
        for row in rows:
            JobStore(client).enqueue(ConsoleRequest(task_id=str(row["id"])))
            connection.execute(
                "UPDATE console_tasks SET published_at=now() WHERE id=%s", (row["id"],)
            )
    return len(rows)
