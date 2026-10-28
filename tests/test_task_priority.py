import json
import threading
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from shared.task_priority import (
    PriorityStop,
    TaskDeferred,
    document_checkpoint,
    next_message,
    priority,
)


class TaskPriorityTest(unittest.TestCase):
    @contextmanager
    def records(self, rows):
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = rows

        @contextmanager
        def transaction():
            yield connection

        with patch("shared.task_priority.transaction", transaction):
            yield connection

    def test_clients_then_training_then_resources_then_translation(self):
        self.assertEqual(priority("vision", "analysis", {}), 0)
        self.assertEqual(priority("vision", "import_upload", {}), 0)
        self.assertEqual(priority("documents", "rag", {"action": "parcel"}), 0)
        self.assertEqual(priority("documents", "rag", {"action": "search"}), 0)
        self.assertEqual(priority("vision", "training", {}), 1)
        self.assertEqual(priority("vision", "embeddings_train", {}), 1)
        self.assertEqual(priority("documents", "search", {}), 2)
        self.assertEqual(priority("documents", "rag", {"action": "prepare"}), 2)
        self.assertEqual(priority("documents", "translate", {}), 3)

    def test_existing_pending_translations_do_not_block_new_collections_or_dossiers(self):
        rows = [
            {"id": "translation", "kind": "translate", "request": {}, "status": "queued"},
            {"id": "collect", "kind": "search", "request": {}, "status": "queued"},
            {"id": "dossier", "kind": "rag", "request": {"action": "parcel"}, "status": "queued"},
        ]
        messages = [(f"{i}-0", {"task_id": row["id"]}) for i, row in enumerate(rows, 1)]
        client = MagicMock()
        client.xreadgroup.side_effect = [[("stream", [messages[-1]])], [("stream", messages)]]
        with self.records(rows):
            self.assertEqual(
                next_message(client, "stream", "group", "one", "documents"), messages[-1]
            )

    def test_new_analysis_precedes_interrupted_training_and_fifo_breaks_ties(self):
        jobs = [
            {"id": "train", "kind": "train_classifier", "request": {}, "status": "queued"},
            {"id": "analysis1", "kind": "analysis", "request": {}, "status": "queued"},
            {"id": "analysis2", "kind": "analysis", "request": {}, "status": "queued"},
        ]
        messages = [(f"{i}-0", {"id": job["id"]}) for i, job in enumerate(jobs, 1)]
        client = MagicMock()
        client.xreadgroup.side_effect = [[("stream", messages)], [("stream", messages)]]
        client.mget.return_value = [json.dumps(job) for job in jobs]
        self.assertEqual(next_message(client, "stream", "group", "one", "vision"), messages[1])

    def test_training_waits_for_documentary_client_without_restarting_in_a_loop(self):
        client = MagicMock()
        message = ("1-0", {"id": "train"})
        client.xreadgroup.side_effect = [[("stream", [message])], [("stream", [message])]]
        client.mget.return_value = [json.dumps({"kind": "train_classifier", "request": {}})]
        with patch("shared.task_priority.has_client_work", return_value=True):
            self.assertIsNone(next_message(client, "stream", "group", "one", "vision"))

    def test_training_yields_to_client_and_preserves_shutdown(self):
        shutdown = threading.Event()
        stop = PriorityStop(shutdown)
        with patch("shared.task_priority.has_client_work", return_value=True):
            self.assertTrue(stop.is_set())
        shutdown.set()
        self.assertTrue(PriorityStop(shutdown).is_set())

    def test_translation_can_yield_without_counting_as_failure(self):
        with self.records([]) as connection:
            connection.execute.return_value.fetchone.return_value = {"pending": True}
            with self.assertRaises(TaskDeferred):
                document_checkpoint("translation", 3)
            document_checkpoint("client", 0)
