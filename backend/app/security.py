"""Fail-closed HTTP authorization, including ownership of files and job inputs."""

import hmac
import os
import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from psycopg import Connection
from starlette.concurrency import run_in_threadpool

from shared import accounts
from shared.access import principal, video_ids
from shared.review.database import ReviewError, transaction

PUBLIC = {
    "/health",
    "/auth/status",
    "/auth/login",
    "/auth/register",
    "/auth/setup",
    "/auth/reset-password",
}


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = os.getenv(
        "AUTH_ALLOWED_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin and origin not in [o.strip() for o in allowed]:
        raise ReviewError("Origine de la requête refusée", 403)


def owned(c: Connection, table: str, key: str, identifier: str, actor: str) -> None:
    # All table/key values below are static server constants, never request strings.
    row = c.execute(
        f"SELECT 1 FROM {table} WHERE {key}=%s AND actor=%s", (identifier, actor)
    ).fetchone()
    if not row:
        raise ReviewError("Ressource introuvable", 404)


def client_access(
    path: str,
    method: str,
    body: dict[str, Any],
    user: dict[str, Any],
    analysis_id: str | None = None,
) -> None:
    actor = user["id"]
    with transaction() as c:
        if analysis_id:
            owned(c, "console_tasks", "id::text", analysis_id, actor)
        videos = None

        def video(identifier):
            nonlocal videos
            if videos is None:
                videos = set(video_ids(c, actor))
            if identifier not in videos:
                raise ReviewError("Vidéo introuvable", 404)

        def sample(identifier):
            row = c.execute(
                """SELECT f.video_id FROM review_samples s JOIN review_frames f
              ON f.id=s.frame_id WHERE s.id=%s""",
                (identifier,),
            ).fetchone()
            if not row:
                raise ReviewError("Observation introuvable", 404)
            video(row["video_id"])

        if path.startswith("/auth/"):
            return
        if path == "/console/uploads" and method == "POST":
            return
        if path == "/console/videos/local":
            raise ReviewError("Import local réservé à l'administration", 403)
        if match := re.fullmatch(r"/console/uploads/([^/]+)(?:/chunks/\d+|/complete)?", path):
            owned(c, "console_uploads", "id::text", match[1], actor)
            return
        if path in ("/console/videos", "/console/tasks", "/console/models") and method == "GET":
            return  # Lists apply the same ownership scope before pagination.
        if match := re.fullmatch(
            r"/console/videos/([^/]+)(?:/(file|analyze|prepare-review))?", path
        ):
            video(match[1])
            if body.get("shadow_model_id"):
                raise ReviewError("Réglage réservé à l'administration", 403)
            return
        if match := re.fullmatch(
            r"/console/tasks/([^/]+)(?:/(?:logs|cancel|artifacts/[^/]+))?", path
        ):
            owned(c, "console_tasks", "id::text", match[1], actor)
            return
        if path in ("/parcels/options", "/parcels/corpora"):
            for identifier in body.get("video_ids", []):
                video(identifier)
            return
        if path == "/parcels/import-status":
            for identifier in body.get("task_ids", []):
                owned(c, "console_tasks", "id::text", identifier, actor)
            return
        if match := re.fullmatch(r"/parcels/corpora/([^/]+)(?:/(?:profile|dossiers))?", path):
            owned(c, "parcel_corpora", "id::text", match[1], actor)
            return
        if match := re.fullmatch(r"/parcels/videos/([^/]+)(?:/dossiers)?", path):
            video(match[1])
            identifier = body.get("analysis_id")
            if identifier:
                owned(c, "console_tasks", "id::text", identifier, actor)
            return
        if match := re.fullmatch(r"/parcels/dossiers/([^/]+)/export", path):
            owned(c, "parcel_dossiers", "id::text", match[1], actor)
            return
        if (
            path == "/review/species"
            or path in ("/review/videos", "/review/samples")
            and method == "GET"
        ):
            return
        if path == "/review/samples/batch-decisions" and method == "POST":
            for item in body.get("items", []):
                if not isinstance(item, dict):
                    raise ReviewError("Sélection d'observations invalide", 422)
                sample(item.get("sample_id"))
            return
        if match := re.fullmatch(r"/review/videos/([^/]+)/imports", path):
            video(match[1])
            return
        if match := re.fullmatch(
            r"/review/samples/([^/]+)(?:/(?:history|decisions|images/[^/]+))?", path
        ):
            sample(match[1])
            return
        if match := re.fullmatch(r"/review/operations/([^/]+)", path):
            owned(c, "review_operations", "id::text", match[1], actor)
            return
        if path.startswith("/documents") and method == "GET":
            if match := re.fullmatch(r"/documents/tasks/([^/]+)(?:/events)?", path):
                owned(c, "document_tasks", "id::text", match[1], actor)
            elif path in ("/documents/watches", "/documents/search-profiles"):
                raise ReviewError("Réservé à l'administration", 403)
            return
        if path in ("/rag/search", "/rag/recommendations") and method == "POST":
            for identifier in body.get("video_ids", []):
                video(identifier)
            return
        if match := re.fullmatch(r"/rag/runs/([^/]+)(?:/export)?", path):
            row = c.execute(
                "SELECT task_id FROM rag_runs WHERE id::text=%s", (match[1],)
            ).fetchone()
            if not row:
                raise ReviewError("Rapport introuvable", 404)
            owned(c, "document_tasks", "id::text", str(row["task_id"]), actor)
            return
    raise ReviewError("Action réservée à l'administration", 403)


async def authorize_request(request: Request) -> AsyncIterator[None]:
    path = request.url.path.rstrip("/") or "/"
    mutating = request.method not in ("GET", "HEAD", "OPTIONS")
    if mutating:
        check_origin(request)
    if path in PUBLIC:
        yield
        return
    token = request.cookies.get(accounts.COOKIE)
    user = await run_in_threadpool(accounts.session_user, token)
    if mutating and not hmac.compare_digest(
        request.headers.get("X-CSRF-Token", "").encode(), accounts.csrf(token).encode()
    ):
        raise ReviewError("Protection CSRF : rechargez la page", 403)
    request.state.user = user
    context_token = principal.set(user)
    try:
        if user["role"] != "admin":
            body = {}
            # FastAPI also accepts +json media types and JSON without Content-Type.
            # Inspect the same bytes regardless of the advertised media type.
            if mutating:
                try:
                    body = await request.json()
                    if not isinstance(body, dict):
                        body = {}
                except ValueError:
                    pass
            await run_in_threadpool(
                client_access,
                path,
                request.method,
                body,
                user,
                request.query_params.get("analysis_id"),
            )
        yield
    finally:
        principal.reset(context_token)
