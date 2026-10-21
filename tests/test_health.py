from unittest.mock import MagicMock

import pytest
from app.config import database_url
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.parametrize("postgres_ok,redis_ok", [(True, True), (False, True), (True, False)])
def test_health_reports_dependencies(postgres_ok: bool, redis_ok: bool) -> None:
    with TestClient(app) as client:
        database = MagicMock()
        connection = database.connect.return_value.__enter__.return_value
        connection.execute.return_value.scalar_one_or_none.return_value = (
            "0.8.1" if postgres_ok else None
        )
        redis = MagicMock()
        redis.ping.return_value = redis_ok
        app.state.database = database
        app.state.redis = redis
        response = client.get("/health")
    assert response.status_code == (200 if postgres_ok and redis_ok else 503)
    assert response.json()["checks"] == {
        "postgres": "ok" if postgres_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }


def test_health_handles_connection_failures_without_leaking_secrets() -> None:
    with TestClient(app) as client:
        database, redis = MagicMock(), MagicMock()
        database.connect.side_effect = RuntimeError("secret connection credentials")
        redis.ping.side_effect = RuntimeError("secret redis credentials")
        app.state.database, app.state.redis = database, redis
        response = client.get("/health")
    assert response.status_code == 503
    assert "secret" not in response.text


def test_database_password_with_special_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "abc@:/%123")
    assert database_url().password == "abc@:/%123"
