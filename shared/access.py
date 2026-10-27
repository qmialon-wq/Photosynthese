"""Request ownership context. Background workers deliberately have no HTTP scope."""

from contextvars import ContextVar
from typing import Any

from psycopg import Connection

principal: ContextVar[dict[str, Any] | None] = ContextVar("authenticated_principal", default=None)


def actor_scope() -> str | None:
    user = principal.get()
    return user["id"] if user and user["role"] != "admin" else None


def video_ids(connection: Connection, actor: str | None = None) -> list[str] | None:
    actor = actor or actor_scope()
    if not actor:
        return None
    rows = connection.execute(
        """SELECT v.id,v.sha256 FROM console_videos v
      JOIN console_tasks t ON t.result->>'video_id'=v.id
      WHERE t.actor=%s AND t.kind IN ('import_upload','import_local') AND t.status='completed'
      UNION SELECT video_id,video_id FROM review_imports WHERE actor=%s""",
        (actor, actor),
    ).fetchall()
    return sorted({str(value) for row in rows for value in row.values()})
