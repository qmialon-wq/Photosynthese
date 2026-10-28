"""Bounded administrator view of durable worker activity."""

import os
import time
from datetime import UTC, datetime
from typing import Any

from redis.exceptions import RedisError

from shared.review.database import transaction
from shared.task_priority import priority_sql
from shared.worker_runtime import heartbeat_is_fresh, heartbeat_key


def activity(client: Any) -> dict[str, Any]:
    roles = ("vision", "documents")
    try:
        signals = client.mget([heartbeat_key(role) for role in roles])
    except RedisError:
        signals = [None, None]
        available = False
    else:
        available = True
    now = time.time()
    workers = []
    with transaction() as connection:
        for index, role in enumerate(roles):
            # Table names and expressions are static constants, never user input.
            table, logs = (
                ("console_tasks", "console_logs")
                if role == "vision"
                else ("document_tasks", "document_events")
            )
            progress = "t.progress" if role == "vision" else "'{}'::jsonb"
            counts = connection.execute(f"""SELECT
                count(*) FILTER (WHERE status='running') AS running,
                count(*) FILTER (WHERE status='queued') AS queued
                FROM {table}""").fetchone()
            tasks = connection.execute(f"""SELECT t.id,t.kind,t.status,t.created_at,t.error,
                {progress} AS progress, {priority_sql(role)} AS priority,
                coalesce(t.request->>'model_name',t.request->>'collection_species',
                    t.request->>'action') AS detail,
                coalesce((SELECT jsonb_agg(line ORDER BY line.id) FROM
                    (SELECT id,message,created_at FROM {logs} WHERE task_id=t.id
                     ORDER BY id DESC LIMIT 20) line),'[]'::jsonb) AS logs
                FROM {table} t
                WHERE t.status IN ('running','queued')
                    OR t.finished_at > now() - interval '15 minutes'
                ORDER BY CASE t.status WHEN 'running' THEN 0 WHEN 'queued' THEN 1 ELSE 2 END,
                    {priority_sql(role)},
                    CASE WHEN t.status='queued' THEN t.created_at END ASC,
                    t.created_at DESC LIMIT 6""").fetchall()
            workers.append(
                {
                    "role": role,
                    "online": heartbeat_is_fresh(
                        signals[index],
                        float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30")),
                        now,
                    )
                    if available
                    else None,
                    **counts,
                    "tasks": tasks,
                }
            )
    return {"updated_at": datetime.now(UTC), "workers": workers}
