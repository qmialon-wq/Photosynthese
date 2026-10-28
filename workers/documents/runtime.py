"""Consommateur documentaire Redis Streams, outbox SQL et ordonnanceur indépendant."""

import logging
import os
import signal
import threading
import time
from typing import Any

from redis import Redis
from redis.exceptions import ResponseError

from shared.documents import service
from shared.documents.config import DocumentSettings
from shared.review.database import jsonb
from shared.task_priority import (
    TaskDeferred,
    next_message,
    priority,
    priority_sql,
    recover_interrupted,
)
from shared.worker_runtime import heartbeat_key

from .http import SafeHTTP
from .ingestion import Ingestor

STREAM, GROUP = "biosentinelle:documents:jobs", "documents"
logger = logging.getLogger(__name__)


def ensure_group(client: Redis) -> None:
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def publish_pending(client: Any) -> int:
    with service.transaction() as connection:
        rows = connection.execute(f"""SELECT id FROM document_tasks t WHERE status='queued'
            AND published_at IS NULL ORDER BY {priority_sql("documents")},created_at,id
            FOR UPDATE SKIP LOCKED LIMIT 20""").fetchall()
        for row in rows:
            client.xadd(STREAM, {"task_id": str(row["id"])})
            connection.execute(
                "UPDATE document_tasks SET published_at=now() WHERE id=%s", (row["id"],)
            )
        return len(rows)


def execute_priority_report(settings: DocumentSettings) -> bool:
    """Interactive dossiers should not wait behind hundreds of queued translations.

    The normal stream delivery remains durable and will ACK the completed task later.
    execute() owns the same per-task advisory lock for both delivery paths.
    """
    with service.transaction() as connection:
        row = connection.execute(
            """SELECT id FROM document_tasks WHERE status IN ('queued','running') AND kind='rag'
            AND request->>'action' IN ('parcel','report') ORDER BY created_at,id LIMIT 1"""
        ).fetchone()
    return execute(str(row["id"]), settings) if row else False


def execute(identifier: str, settings: DocumentSettings) -> bool:
    with service.transaction() as lock:
        acquired = lock.execute(
            "SELECT pg_try_advisory_lock(hashtextextended(%s::text,12)) AS ok", (identifier,)
        ).fetchone()["ok"]
        lock.commit()
        if not acquired:
            return False
        try:
            task = service.task(identifier)
            if task["status"] in ("completed", "partial", "error"):
                return True
            deferred = False
            if task["attempts"] >= 3:
                with service.transaction() as connection:
                    connection.execute(
                        """UPDATE document_tasks SET status='error',finished_at=now(),
                        error='Traitement interrompu trois fois ; relancer explicitement'
                        WHERE id=%s""",
                        (identifier,),
                    )
                    service.event(
                        identifier,
                        "error",
                        "Limite de reprises après interruption atteinte",
                        level="error",
                        connection=connection,
                    )
                return True
            with service.transaction() as connection:
                connection.execute(
                    """UPDATE document_tasks SET status='running',
                    started_at=coalesce(started_at,now()),
                    attempts=attempts+1,error=NULL WHERE id=%s""",
                    (identifier,),
                )
                service.event(
                    identifier,
                    "start",
                    "Début du passage",
                    data={"kind": task["kind"], "attempt": task["attempts"] + 1},
                    connection=connection,
                )
            http = SafeHTTP(settings)
            ingestor = Ingestor(settings, http, identifier)
            ingestor.priority = priority("documents", task["kind"], task["request"])
            http.log = ingestor.log
            try:
                result = ingestor.perform(task["kind"], task["request"], task["actor"])
                status = "completed"
                if (
                    result.get("target_reached") is False
                    or result.get("errors")
                    or (
                        result.get("inaccessible") and not task["request"].get("collection_species")
                    )
                ):
                    status = "partial"
                if task["kind"] == "search" and not result.get("observed") and result.get("errors"):
                    status = "error"
                error = (
                    "Aucune notice récupérée ; consulter les événements"
                    if status == "error"
                    else None
                )
            except TaskDeferred as exc:
                deferred = True
                result, status, error = task.get("result") or {}, "queued", None
                service.event(identifier, "priority", str(exc))
            except Exception as exc:
                logger.exception("Échec de la tâche documentaire %s", identifier)
                result, status, error = {}, "error", f"{type(exc).__name__}: {str(exc)[:2000]}"
            finally:
                http.close()
            with service.transaction() as connection:
                connection.execute(
                    """UPDATE document_tasks SET status=%s,result=%s,error=%s,
                    finished_at=CASE WHEN %s THEN NULL ELSE now() END,
                    attempts=attempts-CASE WHEN %s THEN 1 ELSE 0 END WHERE id=%s""",
                    (status, jsonb(result), error, deferred, deferred, identifier),
                )
                service.event(
                    identifier,
                    "finish",
                    error
                    or (
                        "Tâche en attente d'une priorité supérieure"
                        if deferred
                        else "Passage terminé"
                    ),
                    level="error" if error else "info",
                    data={"status": status, "result": result},
                    connection=connection,
                )
            return not deferred
        finally:
            lock.execute("SELECT pg_advisory_unlock(hashtextextended(%s::text,12))", (identifier,))


def consume_one(client: Redis, settings: DocumentSettings) -> bool:
    client.xautoclaim(STREAM, GROUP, "documents-single", 30000, "0-0", count=256)
    message = next_message(client, STREAM, GROUP, "documents-single", "documents")
    if message is None:
        return False
    message_id, values = message
    if execute(values["task_id"], settings):
        client.xack(STREAM, GROUP, message_id)
        client.xdel(STREAM, message_id)
    return True


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = DocumentSettings()
    interval = float(os.getenv("WORKER_HEARTBEAT_SECONDS", "5"))
    max_age = float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30"))
    if interval <= 0 or max_age <= interval * 2:
        raise ValueError("Délai de heartbeat documentaire invalide")
    settings.root.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    client = Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=4,
    )
    ensure_group(client)
    recover_interrupted("documents")

    def ticker() -> None:
        while not stop.is_set():
            try:
                client.set(heartbeat_key("documents"), str(time.time()), ex=int(max_age) + 1)
                service.schedule_due()
                from shared.parcels.service import schedule

                schedule()
                publish_pending(client)
            except Exception:
                logger.exception("Échec du heartbeat ou de l'ordonnanceur documentaire")
            stop.wait(interval)

    thread = threading.Thread(target=ticker, daemon=True)
    thread.start()
    logger.info("Worker documentaire prêt ; aucune veille créée implicitement")
    try:
        while not stop.is_set():
            if not consume_one(client, settings):
                stop.wait(0.5)
    finally:
        stop.set()
        thread.join(timeout=5)
        client.delete(heartbeat_key("documents"))
        client.close()
