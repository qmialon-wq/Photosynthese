"""Projection PostgreSQL des fichiers persistants, rejouable sans doublons."""

import os
from typing import Any


def connect() -> Any:
    import psycopg

    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "biosentinelle"),
        user=os.getenv("POSTGRES_USER", "biosentinelle"),
        password=os.getenv("POSTGRES_PASSWORD", "biosentinelle_local"),
        connect_timeout=3,
        options="-c statement_timeout=3000",
    )


def project_run(metadata: dict[str, Any], events: list[dict[str, Any]]) -> None:
    from psycopg.types.json import Jsonb

    with connect() as connection:
        connection.execute(
            "INSERT INTO training_runs(run_id,status,metadata) VALUES (%s,%s,%s) "
            "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, "
            "metadata=excluded.metadata,updated_at=now()",
            (metadata["run_id"], metadata["status"], Jsonb(metadata)),
        )
        for event in events:
            connection.execute(
                "INSERT INTO training_metrics(run_id,event_key,metrics) VALUES (%s,%s,%s) "
                "ON CONFLICT(run_id,event_key) DO UPDATE SET metrics=excluded.metrics",
                (metadata["run_id"], event["event_key"], Jsonb(event)),
            )
