from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import create_engine, text

from app.config import database_url, redis_url
from app.training import router as training_router
from app.vision import router as vision_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database = create_engine(database_url(), pool_pre_ping=True)
    app.state.redis = Redis.from_url(
        redis_url(), socket_connect_timeout=2, socket_timeout=2, decode_responses=True
    )
    yield
    app.state.redis.close()
    app.state.database.dispose()


app = FastAPI(title="BioSentinelle Normandie", version="0.1.0", lifespan=lifespan)
app.include_router(vision_router)
app.include_router(training_router)


@app.get("/health")
def health() -> JSONResponse:
    """Sonde courte exécutée dans le pool de threads, sans traitement vidéo."""
    checks: dict[str, str] = {}
    try:
        with app.state.database.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            vector_version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
            checks["postgres"] = "ok" if vector_version else "error"
    except Exception:
        checks["postgres"] = "error"
    try:
        checks["redis"] = "ok" if app.state.redis.ping() else "error"
    except Exception:
        checks["redis"] = "error"
    ready = all(value == "ok" for value in checks.values())
    body: dict[str, Any] = {"status": "ok" if ready else "error", "checks": checks}
    return JSONResponse(body, status_code=200 if ready else 503)
