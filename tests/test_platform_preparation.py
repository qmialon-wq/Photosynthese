import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from infra.prepare_platform import Preparation


class PreparationTest(unittest.TestCase):
    def test_resume_reuses_submitted_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            submit = Mock(return_value={"id": "durable-task"})
            first = Preparation("documents", root=root)
            first.job("collect", submit, lambda _: {"status": "completed", "result": {"n": 3}})
            resumed = Preparation("documents", root=root)
            result = resumed.job(
                "collect", submit, lambda _: {"status": "completed", "result": {"n": 3}}
            )
            self.assertEqual(result, {"n": 3})
            submit.assert_called_once()

    def test_partial_collection_finishes_without_waiting_forever(self):
        with tempfile.TemporaryDirectory() as directory:
            preparation = Preparation("documents", root=Path(directory))
            result = preparation.job(
                "collect",
                lambda: {"id": "partial-task"},
                lambda _: {"status": "partial", "result": {"observed": 2}},
            )
            self.assertEqual(result, {"observed": 2})

    def test_required_failure_stops_but_optional_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            preparation = Preparation("vision", root=Path(directory))

            def failed(_):
                return {"status": "error", "error": "missing resource"}

            with self.assertRaisesRegex(RuntimeError, "missing resource"):
                preparation.job("training", lambda: {"id": "failed-task"}, failed)
            result = preparation.job("training", Mock(), failed, optional=True)
            self.assertIsNone(result)
            self.assertEqual(preparation.state["jobs"]["training"]["status"], "error")
