from typing import Any

from .database import transaction


def publish_pending(client: Any) -> int:
    from shared.vision_jobs import JobStore, ReviewRequest

    with transaction() as connection:
        rows = connection.execute(
            "SELECT id FROM review_operations WHERE status='queued' AND published_at IS NULL "
            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20"
        ).fetchall()
        for row in rows:
            JobStore(client).enqueue(ReviewRequest(operation_id=str(row["id"])))
            connection.execute(
                "UPDATE review_operations SET published_at=now() WHERE id=%s", (row["id"],)
            )
    return len(rows)
