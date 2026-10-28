"""Server-owned priorities, including messages already delivered to Redis consumers."""

import json
import os
import threading
import time
from functools import lru_cache
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from shared.review.database import transaction

TRAINING_KINDS = (
    "training",
    "evaluation",
    "register_model",
    "classification_dataset",
    "embeddings_extract",
    "embeddings_train",
    "embeddings_cluster",
    "classifiers_compare",
    "model_promote",
    "model_rollback",
)
INTERACTIVE_JOBS = "biosentinelle:vision:interactive"


@lru_cache(maxsize=1)
def priority_client() -> Redis:
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def priority(role: str, kind: str, request: dict[str, Any]) -> int:
    if role == "vision":
        return 1 if kind in (*TRAINING_KINDS, "train_classifier", "evaluate_classifier") else 0
    if kind == "translate":
        return 3
    if kind == "import" or (
        kind == "rag"
        and request.get("action")
        in (
            "parcel",
            "report",
            "search",
            "result",
        )
    ):
        return 0
    return 2


def priority_sql(role: str, alias: str = "t") -> str:
    """Only called with fixed, internal role and alias constants."""
    if role == "vision":
        kinds = ",".join(f"'{kind}'" for kind in TRAINING_KINDS)
        return f"CASE WHEN {alias}.kind IN ({kinds}) THEN 1 ELSE 0 END"
    return (
        f"CASE WHEN {alias}.kind='translate' THEN 3 "
        f"WHEN {alias}.kind='import' OR ({alias}.kind='rag' AND "
        f"{alias}.request->>'action' IN ('parcel','report','search','result')) THEN 0 ELSE 2 END"
    )


def has_client_work() -> bool:
    with transaction() as connection:
        pending = connection.execute(f"""SELECT EXISTS(
            SELECT 1 FROM console_tasks t WHERE status IN ('queued','running')
                AND ({priority_sql("vision")})=0
            UNION ALL SELECT 1 FROM document_tasks t WHERE status IN ('queued','running')
                AND ({priority_sql("documents")})=0) AS pending""").fetchone()["pending"]
    if pending:
        return True
    try:
        return bool(priority_client().zcard(INTERACTIVE_JOBS))
    except RedisError:
        return False  # The consumer's existing lease monitor handles Redis outages.


class PriorityStop:
    """Cooperative training stop; completed epochs remain in the existing checkpoint."""

    def __init__(self, shutdown: threading.Event | None) -> None:
        self.shutdown = shutdown
        self.checked_at = float("-inf")
        self.pending = False

    def is_set(self) -> bool:
        if self.shutdown is not None and self.shutdown.is_set():
            return True
        now = time.monotonic()
        if now - self.checked_at >= 1:
            self.pending = has_client_work()
            self.checked_at = now
        return self.pending


class TaskDeferred(Exception):
    pass


def recover_interrupted(role: str) -> None:
    """Only requeue orphaned SQL tasks; an actively held task lock is left alone."""
    table, salt = ("console_tasks", 1) if role == "vision" else ("document_tasks", 12)
    with transaction() as connection:
        rows = connection.execute(f"SELECT id FROM {table} WHERE status='running'").fetchall()
    for row in rows:
        with transaction() as connection:
            acquired = connection.execute(
                "SELECT pg_try_advisory_lock(hashtextextended(%s::text,%s)) AS ok",
                (str(row["id"]), salt),
            ).fetchone()["ok"]
            if not acquired:
                continue
            try:
                connection.execute(
                    f"UPDATE {table} SET status='queued',finished_at=NULL "
                    "WHERE id=%s AND status='running'",
                    (row["id"],),
                )
                connection.commit()
            finally:
                connection.execute(
                    "SELECT pg_advisory_unlock(hashtextextended(%s::text,%s))",
                    (str(row["id"]), salt),
                )


def document_checkpoint(identifier: str, rank: int) -> None:
    if rank == 0:
        return
    with transaction() as connection:
        pending = connection.execute(
            f"""SELECT EXISTS(
            SELECT 1 FROM document_tasks t WHERE status='queued' AND id<>%s
                AND ({priority_sql("documents")}) < %s) AS pending""",
            (identifier, rank),
        ).fetchone()["pending"]
    if pending:
        raise TaskDeferred("Mise en attente pour une tâche plus prioritaire")


def next_message(
    client: Any,
    stream: str,
    group: str,
    consumer: str,
    role: str,
) -> tuple[str, dict[str, str]] | None:
    # Deliver all new messages before ranking. Merely sorting the SQL outbox would
    # leave older translations/training jobs at the head of the existing stream.
    while True:
        delivered = client.xreadgroup(group, consumer, {stream: ">"}, count=256)
        if not delivered or not delivered[0][1] or len(delivered[0][1]) < 256:
            break
    messages = []
    cursor = "0"
    while True:
        pending = client.xreadgroup(group, consumer, {stream: cursor}, count=256)
        batch = pending[0][1] if pending else []
        messages.extend(batch)
        if len(batch) < 256:
            break
        cursor = batch[-1][0]
    if not messages:
        return None
    jobs: dict[str, Any] = {}
    if role == "vision":
        identifiers = [fields["id"] for _, fields in messages]
        values = client.mget([f"biosentinelle:vision:job:{key}" for key in identifiers])
        jobs = {
            key: json.loads(value)
            for key, value in zip(identifiers, values, strict=True)
            if value is not None
        }
        task_ids = [
            job["request"]["task_id"] for job in jobs.values() if job.get("kind") == "console"
        ]
        table = "console_tasks"
    else:
        task_ids = [fields["task_id"] for _, fields in messages]
        table = "document_tasks"
    records = {}
    if task_ids:
        with transaction() as connection:
            rows = connection.execute(
                f"SELECT id,kind,request,status FROM {table} WHERE id=ANY(%s::uuid[])",
                (task_ids,),
            ).fetchall()
        records = {str(row["id"]): row for row in rows}

    def order(item: tuple[str, dict[str, str]]) -> tuple[int, tuple[int, ...]]:
        message_id, fields = item
        job = jobs.get(fields.get("id", ""), {})
        row = records.get(fields.get("task_id", job.get("request", {}).get("task_id")), job)
        rank = priority(role, row.get("kind", "analysis"), row.get("request", {}))
        if row.get("status") in ("completed", "partial", "error", "cancelled"):
            rank = -1  # Reconcile any old deliveries already completed through another path.
        return rank, tuple(int(part) for part in message_id.split("-"))

    selected = min(messages, key=order)
    if role == "vision" and order(selected)[0] == 1 and has_client_work():
        return None  # Let the documentary worker finish an interactive dossier first.
    return selected
