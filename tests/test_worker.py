import pytest

from shared.worker_runtime import heartbeat_is_fresh


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False),
        ("invalid", False),
        ("100", True),
        ("70", True),
        ("69", False),
        ("101", False),
        ("nan", False),
    ],
)
def test_heartbeat_rejects_missing_stale_or_invalid_values(
    value: str | None, expected: bool
) -> None:
    assert heartbeat_is_fresh(value, max_age=30, now=100) is expected
