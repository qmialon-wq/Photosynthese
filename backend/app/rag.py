"""Only task submission and stored results: no encoder or LLM loaded in HTTP."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from app.review import Actor
from shared.documents.schemas import SpeciesKey
from shared.rag import service
from shared.rag.schemas import Context, DocumentContext, Evaluation, Index, Report, Search, Taxonomy
from shared.review.database import ReviewError

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/prepare", status_code=202)
def prepare(actor: Actor) -> dict[str, Any]:
    return service.submit("prepare", {}, actor)


@router.post("/index", status_code=202)
def index(body: Index, actor: Actor) -> dict[str, Any]:
    return service.submit("index", body.model_dump(mode="json"), actor)


@router.post("/search", status_code=202)
def search(body: Search, actor: Actor) -> dict[str, Any]:
    return service.submit("search", body.model_dump(mode="json"), actor)


@router.post("/recommendations", status_code=202)
def recommendations(body: Report, actor: Actor) -> dict[str, Any]:
    return service.submit("report", body.model_dump(mode="json"), actor)


@router.post("/evaluate", status_code=202)
def evaluate(body: Evaluation, actor: Actor) -> dict[str, Any]:
    return service.submit("evaluate", body.model_dump(mode="json"), actor)


@router.get("/runs/{identifier}")
def run(identifier: UUID) -> dict[str, Any]:
    return service.run(str(identifier))


@router.get("/runs/{identifier}/export")
def export(identifier: UUID, format: str = "json") -> Response:
    import json

    row = service.run(str(identifier))
    if format == "json":
        content = json.dumps(row, ensure_ascii=False, default=str, indent=2)
        media_type = "application/json"
    elif format == "markdown" and row["kind"] == "report":
        # Pure formatting shared with CLI; no worker/ML dependency in backend.
        from shared.rag.export import markdown

        content, media_type = markdown(row["result"]), "text/markdown"
    else:
        raise ReviewError("Format attendu : json, ou markdown pour un rapport", 422)
    suffix = "json" if format == "json" else "md"
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="biosentinelle-{identifier}.{suffix}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/videos/{video_id}/context")
def context(video_id: str, body: Context, actor: Actor) -> dict[str, Any]:
    return service.video_context(video_id, body, actor)


@router.put("/documents/{identifier}/context")
def document_context(identifier: UUID, body: DocumentContext, actor: Actor) -> dict[str, Any]:
    return service.document_context(str(identifier), body, actor)


@router.put("/taxonomy/{species}")
def taxonomy(species: SpeciesKey, body: Taxonomy, actor: Actor) -> dict[str, Any]:
    return service.taxonomy(species, body, actor)
