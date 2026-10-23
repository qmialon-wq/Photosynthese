from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import Field

from app.review import Actor
from shared.documents.schemas import Body
from shared.parcels import corpora, service
from shared.parcels.schemas import CorpusCreate, CorpusRequest, Profile
from shared.review.database import ReviewError, transaction

router = APIRouter(prefix="/parcels", tags=["parcel-projects"])


class DossierRequest(Body):
    analysis_id: UUID
    profile_revision: int = Field(gt=0)


class Imports(Body):
    task_ids: list[UUID] = Field(min_length=1, max_length=1000)


@router.post("/import-status")
def import_status(body: Imports) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            """SELECT id,status,result,error FROM console_tasks
            WHERE id=ANY(%s::uuid[]) AND kind='import_upload'""",
            ([str(i) for i in body.task_ids],),
        ).fetchall()


@router.get("/options")
def options() -> dict[str, Any]:
    return service.options()


@router.post("/corpora", status_code=201)
def create_corpus(body: CorpusCreate, actor: Actor) -> dict[str, Any]:
    return corpora.create(body.video_ids, actor)


@router.get("/corpora")
def corpus_list() -> list[dict[str, Any]]:
    return corpora.listing()


@router.get("/corpora/{identifier}")
def corpus(identifier: UUID) -> dict[str, Any]:
    return corpora.read(str(identifier))


@router.put("/corpora/{identifier}/profile")
def corpus_profile(identifier: UUID, body: Profile, actor: Actor) -> dict[str, Any]:
    return corpora.save(str(identifier), body, actor)


@router.post("/corpora/{identifier}/dossiers", status_code=202)
def corpus_dossier(identifier: UUID, body: CorpusRequest, actor: Actor) -> dict[str, Any]:
    return corpora.request(str(identifier), body.profile_revision, actor)


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
