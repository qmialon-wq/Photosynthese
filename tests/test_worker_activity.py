import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from redis.exceptions import ConnectionError

from shared.worker_activity import activity


class WorkerActivityTest(unittest.TestCase):
    def snapshot(self, client):
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = {"running": 1, "queued": 5}
        connection.execute.return_value.fetchall.return_value = []

        @contextmanager
        def transaction():
            yield connection

        with patch("shared.worker_activity.transaction", transaction):
            return activity(client)

    def test_worker_without_recent_heartbeat_is_not_reported_online(self):
        client = MagicMock()
        client.mget.return_value = ["100", None]
        with patch("shared.worker_activity.time.time", return_value=110):
            result = self.snapshot(client)
        self.assertTrue(result["workers"][0]["online"])
        self.assertFalse(result["workers"][1]["online"])
        self.assertEqual(result["workers"][0]["queued"], 5)

    def test_redis_failure_preserves_database_activity_with_unknown_health(self):
        client = MagicMock()
        client.mget.side_effect = ConnectionError("offline")
        result = self.snapshot(client)
        self.assertTrue(all(worker["online"] is None for worker in result["workers"]))
        self.assertEqual(result["workers"][0]["running"], 1)
