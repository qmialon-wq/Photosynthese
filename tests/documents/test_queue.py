from unittest.mock import MagicMock

import pytest

from shared.documents.config import DocumentSettings
from workers.documents import runtime


@pytest.mark.parametrize("finished", [True, False])
def test_queue_acknowledges_only_after_processing(monkeypatch, finished):
    client = MagicMock()
    client.xautoclaim.return_value = ["0-0", []]
    client.xreadgroup.return_value = [("stream", [("1-0", {"task_id": "test-only"})])]
    calls = []
    monkeypatch.setattr(runtime, "execute", lambda *_: calls.append("execute") or finished)
    client.xack.side_effect = lambda *_: calls.append("ack")
    runtime.consume_one(client, DocumentSettings())
    assert calls == (["execute", "ack"] if finished else ["execute"])
    assert client.xdel.call_count == int(finished)
