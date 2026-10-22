from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/training", tags=["training"])


def rows(request: Request, sql: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        with request.app.state.database.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            return [dict(row) for row in connection.execute(text(sql), parameters).mappings()]
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Métriques PostgreSQL indisponibles") from exc


@router.get("/runs")
def list_runs(
    request: Request, limit: int = Query(default=50, ge=1, le=200)
) -> list[dict[str, Any]]:
    return rows(
        request,
        "SELECT * FROM training_runs ORDER BY updated_at DESC LIMIT :limit",
        {"limit": limit},
    )


@router.get("/runs/{run_id}")
def read_run(run_id: str, request: Request) -> dict[str, Any]:
    result = rows(request, "SELECT * FROM training_runs WHERE run_id=:run_id", {"run_id": run_id})
    if not result:
        raise HTTPException(404, "Run inconnu")
    return result[0]


@router.get("/runs/{run_id}/metrics")
def read_metrics(run_id: str, request: Request) -> list[dict[str, Any]]:
    read_run(run_id, request)
    return rows(
        request,
        "SELECT event_key, metrics FROM training_metrics WHERE run_id=:run_id "
        "ORDER BY CASE WHEN metrics->>'phase'='head' THEN 0 ELSE 1 END, "
        "(metrics->>'epoch')::integer",
        {"run_id": run_id},
    )
