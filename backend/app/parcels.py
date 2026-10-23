from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import Field

from app.review import Actor
from shared.documents.schemas import Body
from shared.parcels import service
from shared.parcels.schemas import Profile
from shared.review.database import ReviewError

router = APIRouter(prefix="/parcels", tags=["parcel-projects"])


class DossierRequest(Body):
    analysis_id: UUID
    profile_revision: int = Field(gt=0)


@router.get("/options")
def options() -> dict[str, Any]:
    return service.options()


@router.get("/videos/{video_id}")
def state(video_id: str, analysis_id: UUID | None = None) -> dict[str, Any]:
    return service.state(video_id, str(analysis_id) if analysis_id else None)


@router.put("/videos/{video_id}")
def save(video_id: str, body: Profile, actor: Actor) -> dict[str, Any]:
    return service.save(video_id, body, actor)


@router.post("/videos/{video_id}/dossiers", status_code=202)
def request(video_id: str, body: DossierRequest, actor: Actor) -> dict[str, Any]:
    return service.request(video_id, str(body.analysis_id), body.profile_revision, actor)


@router.get("/dossiers/{identifier}/export")
def export(identifier: UUID, format: str = "text") -> Response:
    import json

    from shared.parcels.report import render

    row = service.dossier(str(identifier))
    if row["status"] != "completed":
        raise ReviewError("Le dossier n'est pas encore disponible", 409)
    if format not in ("text", "markdown", "json"):
        raise ReviewError("Format attendu : text, markdown ou json", 422)
    text = (
        json.dumps(row["result"], ensure_ascii=False, indent=2)
        if format == "json"
        else render(row["result"], markdown=format == "markdown")
    )
    suffix = {"text": "txt", "markdown": "md", "json": "json"}[format]
    return Response(
        text,
        media_type="application/json" if format == "json" else "text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="dossier-parcelle-{identifier}.{suffix}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
