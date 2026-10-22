import os
import time

import httpx
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.config import database_url, redis_url
from redis import Redis
from sqlalchemy import create_engine, text

from shared.worker_runtime import heartbeat_is_fresh, heartbeat_key

pytestmark = pytest.mark.integration


def test_api_and_frontend_proxy() -> None:
    backend = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    frontend = os.getenv("FRONTEND_URL", "http://127.0.0.1:8080")
    with httpx.Client(timeout=10) as client:
        direct = client.get(f"{backend}/health")
        proxied = client.get(f"{frontend}/api/health")
        assert direct.status_code == proxied.status_code == 200
        assert direct.json() == proxied.json()
        assert direct.json()["status"] == "ok"
        assert "BioSentinelle" in client.get(frontend).text


def test_postgres_extension_and_migration() -> None:
    engine = create_engine(database_url())
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one()
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == ScriptDirectory.from_config(Config("backend/alembic.ini")).get_current_head()
            )
    finally:
        engine.dispose()


def test_redis_persistence_and_workers() -> None:
    with Redis.from_url(redis_url(), decode_responses=True, socket_timeout=3) as client:
        assert client.ping()
        assert client.config_get("appendonly")["appendonly"] == "yes"
        assert client.config_get("appendfsync")["appendfsync"] == "everysec"
        assert client.config_get("maxmemory-policy")["maxmemory-policy"] == "noeviction"
        for role in ("vision", "documents"):
            assert heartbeat_is_fresh(
                client.get(heartbeat_key(role)),
                float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30")),
                time.time(),
            )
