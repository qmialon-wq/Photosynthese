from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from redis import Redis
from sqlalchemy import create_engine, text

from app.auth import router as auth_router
from app.classification import router as classification_router
from app.config import database_url, redis_url
from app.console import router as console_router
from app.documents import router as documents_router
from app.parcels import router as parcels_router
from app.rag import router as rag_router
from app.review import router as review_router
from app.security import authorize_request
from app.training import router as training_router
from app.vision import router as vision_router
from shared import accounts
from shared.review.database import ReviewError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    accounts.ensure_bootstrap()
    app.state.database = create_engine(database_url(), pool_pre_ping=True)
    app.state.redis = Redis.from_url(
        redis_url(), socket_connect_timeout=2, socket_timeout=2, decode_responses=True
    )
    yield
    app.state.redis.close()
    app.state.database.dispose()


app = FastAPI(
    title="BioSentinelle Normandie",
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(authorize_request)],
)
app.include_router(auth_router)
app.include_router(vision_router)
app.include_router(training_router)
app.include_router(review_router)
app.include_router(console_router)
app.include_router(classification_router)
app.include_router(documents_router)
app.include_router(parcels_router)
app.include_router(rag_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(ReviewError)
async def review_error(request: Request, exc: ReviewError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


@app.exception_handler(OperationalError)
async def review_database_error(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse({"detail": "Stockage PostgreSQL indisponible"}, status_code=503)


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
