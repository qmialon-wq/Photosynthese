from uuid import uuid4

import pytest
from redis import Redis

from shared.documents import service
from shared.task_priority import TaskDeferred, next_message, recover_interrupted
from workers.documents import runtime

pytestmark = pytest.mark.integration


def test_worker_restart_requeues_only_orphaned_tasks(document_db):
    orphan = service.submit("search", {}, "test")
    active = service.submit("translate", {}, "test")
    with service.transaction() as connection:
        connection.execute("UPDATE document_tasks SET status='running',attempts=1")
    with service.transaction() as held:
        held.execute("SELECT pg_advisory_lock(hashtextextended(%s::text,12))", (active["id"],))
        held.commit()
        recover_interrupted("documents")
        assert service.task(active["id"])["status"] == "running"
    assert service.task(orphan["id"])["status"] == "queued"
    assert service.task(orphan["id"])["attempts"] == 1


def test_priority_reorders_messages_already_pending_and_keeps_fifo(document_db):
    import os

    client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    stream = f"test:priority:{uuid4()}"
    group, consumer = "test", "one"
    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
        translation = service.submit("translate", {}, "test")
        first = service.submit("search", {}, "test")
        second = service.submit("search", {}, "test")
        for task in (translation, first, second):
            client.xadd(stream, {"task_id": task["id"]})
        client.xreadgroup(group, consumer, {stream: ">"}, count=20)
        dossier = service.submit("rag", {"action": "parcel"}, "test")
        client.xadd(stream, {"task_id": dossier["id"]})
        message_id, fields = next_message(client, stream, group, consumer, "documents")
        assert fields["task_id"] == dossier["id"]
        client.xack(stream, group, message_id)
        client.xdel(stream, message_id)
        selected = next_message(client, stream, group, consumer, "documents")
        assert selected[1]["task_id"] == first["id"]
    finally:
        client.delete(stream)
        client.close()


def test_deferred_translation_preserves_retry_budget_and_can_resume(document_db, monkeypatch):
    task = service.submit("translate", {"document_id": str(uuid4())}, "test")

    def defer(*args):
        raise TaskDeferred("Collecte prioritaire")

    monkeypatch.setattr(runtime.Ingestor, "perform", defer)
    assert runtime.execute(task["id"], document_db) is False
    deferred = service.task(task["id"])
    assert deferred["status"] == "queued"
    assert deferred["attempts"] == 0
    assert deferred["error"] is None
    assert deferred["finished_at"] is None
    monkeypatch.setattr(runtime.Ingestor, "perform", lambda *args: {"done": True})
    assert runtime.execute(task["id"], document_db) is True
    assert service.task(task["id"])["status"] == "completed"
