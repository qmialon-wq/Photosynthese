"""Read-only progress, including jobs started before structured progress existed."""

from datetime import UTC, datetime


def read(connection, task_id):
    if not task_id:
        return None
    task = connection.execute(
        "SELECT status,started_at,created_at FROM document_tasks WHERE id=%s", (task_id,)
    ).fetchone()
    if not task:
        return None
    events = connection.execute(
        """SELECT id,stage,message,data,created_at FROM document_events
        WHERE task_id=%s AND stage IN ('synthesis','rag_progress') ORDER BY id""",
        (task_id,),
    ).fetchall()
    state, documents, pages, recent = {}, {}, 0, []
    last_document = None
    last_activity = task["started_at"] or task["created_at"]
    for event in events:
        data = event["data"]
        if event["stage"] == "rag_progress":
            state.update(data)
        if data.get("document_id") and "chunks_read" in data:
            last_document = data["document_id"]
            documents[last_document] = max(
                documents.get(last_document, 0), data["chunks_read"]
            )
        if "page" in data:
            pages = max(pages, data["page"])
        last_activity = event["created_at"]
        recent.append({"message": event["message"], "at": event["created_at"]})
    current = None
    if last_document and state.get("phase", "reading") == "reading":
        current = connection.execute(
            "SELECT title FROM scientific_documents WHERE id=%s", (last_document,)
        ).fetchone()
    phase = state.get("phase") or ("writing" if pages else "reading" if documents else "preparing")
    if task["status"] == "queued":
        phase = "queued"
    elif task["status"] in ("completed", "error", "partial"):
        phase = task["status"]
    now = datetime.now(UTC)
    return {
        **state,
        "phase": phase,
        "documents_started": len(documents),
        "chunks_read": sum(documents.values()),
        "pages_done": pages,
        "pages_total": 4,
        "current_document": state.get("current_document") or (current["title"] if current else None),
        "detailed_tracking": bool(state.get("detailed_tracking")),
        "current_document_chunks_read": documents.get(last_document, 0),
        "started_at": task["started_at"],
        "last_activity_at": last_activity,
        "elapsed_seconds": int((now - (task["started_at"] or task["created_at"])).total_seconds()),
        "seconds_since_activity": max(0, int((now - last_activity).total_seconds())),
        "recent": recent[-5:][::-1],
    }
