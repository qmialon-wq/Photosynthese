"""API de veille : métadonnées et soumissions, sans appels scientifiques dans HTTP."""

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse

from app.review import Actor
from shared.documents import corpus, service
from shared.documents.config import DocumentSettings
from shared.documents.relevance import profiles
from shared.documents.schemas import Decision, ManualImport, Search, Selection, SpeciesKey, Watch
from shared.review.database import ReviewError

router = APIRouter(prefix="/documents", tags=["scientific-documents"])


def root() -> Path:
    return DocumentSettings().root.resolve()


@router.get("/species")
def species_catalog() -> list[dict[str, Any]]:
    return corpus.catalog()


@router.get("/search-profiles")
def search_profiles() -> dict[str, Any]:
    return profiles()


@router.post("/search", status_code=202)
def search(
    body: Search, actor: Actor, idempotency_key: str | None = Header(default=None, max_length=128)
) -> dict[str, Any]:
    return service.submit(
        "search",
        {"search": body.model_dump()},
        actor,
        dedup_key=f"search:{actor}:{idempotency_key}" if idempotency_key else None,
    )


@router.post("/watches", status_code=201)
def watch(body: Watch, actor: Actor) -> dict[str, Any]:
    return service.watch(body, actor)


@router.get("/watches")
def watches() -> list[dict[str, Any]]:
    with service.transaction() as connection:
        return connection.execute(
            "SELECT * FROM document_watches ORDER BY created_at DESC"
        ).fetchall()


@router.post("/watches/{identifier}/run", status_code=202)
def run_watch(
    identifier: UUID,
    actor: Actor,
    idempotency_key: str | None = Header(default=None, max_length=128),
) -> dict[str, Any]:
    return service.run_watch(str(identifier), actor, key=idempotency_key)


@router.post("/import", status_code=202)
def manual(body: ManualImport, actor: Actor) -> dict[str, Any]:
    path = (root() / "inbox" / body.path).resolve()
    if not path.is_relative_to(root() / "inbox") or not path.is_file():
        raise ReviewError("Document absent du dossier documents/inbox", 404)
    return service.submit("import", body.model_dump(), actor)


@router.post("/upload", status_code=202)
async def upload(
    request: Request,
    actor: Actor,
    filename: str = Query(max_length=200),
    rights_confirmed: bool = False,
    title: str | None = Query(default=None, max_length=1000),
    doi: str | None = None,
    license: str | None = Query(default=None, max_length=500),
    species: SpeciesKey | None = None,
) -> dict[str, Any]:
    # Transfert brut borné ; parsing, hash, langue et déduplication appartiennent au worker.
    if any(c in filename for c in "/\\:\x00"):
        raise ReviewError("Nom de fichier invalide", 422)
    try:
        body = ManualImport(
            path=f"uploads/{uuid4()}/{filename}",
            rights_confirmed=rights_confirmed,
            title=title,
            doi=doi,
            license=license,
            species=[species] if species else [],
        )
    except ValueError as exc:
        raise ReviewError(str(exc), 422) from exc
    target = root() / "inbox" / body.path
    target.parent.mkdir(parents=True, exist_ok=True)
    max_file_bytes = DocumentSettings().max_file_bytes
    size = 0
    try:
        with target.open("xb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_file_bytes:
                    raise ReviewError("Document trop volumineux", 413)
                output.write(chunk)
        if not size:
            raise ReviewError("Document vide", 422)
        return service.submit("import", body.model_dump(), actor)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


@router.get("/tasks/{identifier}")
def task(identifier: UUID) -> dict[str, Any]:
    return service.task(str(identifier))


@router.get("/tasks")
def tasks(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)
) -> list[dict[str, Any]]:
    with service.transaction() as connection:
        return connection.execute(
            "SELECT * FROM document_tasks ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()


@router.get("/tasks/{identifier}/events")
def events(
    identifier: UUID,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    service.task(str(identifier))
    with service.transaction() as connection:
        return connection.execute(
            "SELECT * FROM document_events WHERE task_id=%s AND id>%s ORDER BY id LIMIT %s",
            (identifier, after, limit),
        ).fetchall()


@router.post("/tasks/{identifier}/retry", status_code=202)
def retry(identifier: UUID, actor: Actor) -> dict[str, Any]:
    previous = service.task(str(identifier))
    if previous["status"] in ("queued", "running"):
        raise ReviewError("La tâche est déjà en cours")
    return service.submit(previous["kind"], previous["request"], actor)


@router.get("")
def listing(
    status: str | None = Query(
        default=None, pattern="^(discovered|imported|indexed|rejected|inaccessible)$"
    ),
    approved_only: bool = False,
    species: SpeciesKey | None = None,
    selected_only: bool = False,
    focus_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    return corpus.listing(species, selected_only, status, approved_only, limit, offset, focus_only)


@router.get("/{identifier}")
def document(identifier: UUID) -> dict[str, Any]:
    row = service.document(str(identifier))
    with service.transaction() as connection:
        return {
            **row,
            "species_links": corpus.links(str(row["id"])),
            "selection_history": connection.execute(
                "SELECT * FROM document_selection_history WHERE document_id=%s ORDER BY id",
                (row["id"],),
            ).fetchall(),
            "provenance": connection.execute(
                "SELECT * FROM document_provenance WHERE document_id=%s ORDER BY id", (row["id"],)
            ).fetchall(),
            "assets": connection.execute(
                "SELECT * FROM document_assets WHERE document_id=%s ORDER BY created_at",
                (row["id"],),
            ).fetchall(),
            "reviews": connection.execute(
                "SELECT * FROM document_reviews WHERE document_id=%s ORDER BY id", (row["id"],)
            ).fetchall(),
        }


@router.post("/{identifier}/review")
def review(identifier: UUID, body: Decision, actor: Actor) -> dict[str, Any]:
    return service.review(str(identifier), body, actor)


@router.put("/{identifier}/species/{species}")
def select_source(
    identifier: UUID, species: SpeciesKey, body: Selection, actor: Actor
) -> dict[str, Any]:
    return corpus.select(str(identifier), species, body.enabled, actor)


@router.post("/{identifier}/fetch", status_code=202)
def fetch(identifier: UUID, actor: Actor) -> dict[str, Any]:
    row = service.document(str(identifier))
    return service.submit("fetch", {"document_id": str(row["id"])}, actor)


@router.get("/{identifier}/chunks")
def chunks(
    identifier: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    row = service.document(str(identifier))
    with service.transaction() as connection:
        return connection.execute(
            """SELECT c.id,c.asset_id,c.page_number,c.ordinal,c.start_char,
            c.end_char,c.text,c.language,c.is_reference
            FROM document_chunks c JOIN document_assets a
            ON a.id=c.asset_id WHERE a.document_id=%s ORDER BY a.id,c.page_number,c.ordinal
            LIMIT %s OFFSET %s""",
            (row["id"], limit, offset),
        ).fetchall()


@router.get("/{identifier}/pages")
def pages(
    identifier: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    row = service.document(str(identifier))
    with service.transaction() as connection:
        return connection.execute(
            """SELECT p.* FROM document_pages p JOIN document_assets a
            ON a.id=p.asset_id WHERE a.document_id=%s
            ORDER BY a.id,p.page_number LIMIT %s OFFSET %s""",
            (row["id"], limit, offset),
        ).fetchall()


@router.get("/{identifier}/assets/{asset_id}", response_class=FileResponse)
def asset(identifier: UUID, asset_id: UUID, inline: bool = False) -> FileResponse:
    row = service.document(str(identifier))
    with service.transaction() as connection:
        file = connection.execute(
            "SELECT * FROM document_assets WHERE id=%s AND document_id=%s", (asset_id, row["id"])
        ).fetchone()
    if file is None:
        raise ReviewError("Fichier inconnu", 404)
    target = (root() / file["storage_key"]).resolve()
    if not target.is_relative_to(root()) or not target.is_file():
        raise ReviewError("Fichier absent du stockage", 404)
    return FileResponse(
        target,
        filename=f"{row['id']}.{file['format']}",
        media_type="application/pdf" if file["format"] == "pdf" else "application/octet-stream",
        content_disposition_type="inline" if inline and file["format"] == "pdf" else "attachment",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )
