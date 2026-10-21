"""Configuration de connexion commune à l'API, Alembic et aux diagnostics."""

import os

from sqlalchemy import URL


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "biosentinelle"),
        password=os.getenv("POSTGRES_PASSWORD", "biosentinelle_local"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "biosentinelle"),
        query={"connect_timeout": "3"},
    )


def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")
