"""Persistance transactionnelle, déduplication et journal de la veille."""

import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from shared.review import database
from shared.review.database import ReviewError, jsonb

from .schemas import Decision, Publication, Watch


@contextmanager
def transaction(write: bool = False) -> Any:
    with database.transaction() as connection:
        if write:
            connection.execute("SELECT pg_advisory_xact_lock(641728104)")
        yield connection


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def event(
    task: str | None,
    stage: str,
    message: str,
    *,
    document: str | None = None,
    level: str = "info",
    data: dict[str, Any] | None = None,
    connection: Any = None,
) -> None:
    if connection is None:
        with transaction() as current:
            return event(
                task, stage, message, document=document, level=level, data=data, connection=current
            )
    connection.execute(
        """INSERT INTO document_events(task_id,document_id,stage,level,message,data)
        VALUES(%s,%s,%s,%s,%s,%s)""",
        (task, document, stage, level, message[:4000], jsonb(data or {})),
    )


def submit(
    kind: str,
    request: dict[str, Any],
    actor: str,
    *,
    dedup_key: str | None = None,
    connection: Any = None,
) -> dict[str, Any]:
    if connection is None:
        with transaction(write=True) as current:
            return submit(kind, request, actor, dedup_key=dedup_key, connection=current)
    row = connection.execute(
        """INSERT INTO document_tasks(id,kind,request,actor,dedup_key)
        VALUES(%s,%s,%s,%s,%s) ON CONFLICT(dedup_key) DO UPDATE SET dedup_key=excluded.dedup_key
        RETURNING id,status,kind,request,actor""",
        (str(uuid4()), kind, jsonb(request), actor, dedup_key),
    ).fetchone()
    if row["kind"] != kind or row["request"] != request or row["actor"] != actor:
        raise ReviewError("Cette clé d'idempotence correspond à une autre requête", 409)
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "status_url": f"/documents/tasks/{row['id']}",
    }


def task(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM document_tasks WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Tâche documentaire inconnue", 404)
    return row


def watch(body: Watch, actor: str) -> dict[str, Any]:
    with transaction(write=True) as connection:
        return connection.execute(
            """INSERT INTO document_watches(id,name,definition,interval_seconds,enabled,actor)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(name) DO UPDATE SET
            definition=excluded.definition,interval_seconds=excluded.interval_seconds,
            enabled=excluded.enabled,actor=excluded.actor RETURNING *""",
            (
                str(uuid4()),
                body.name,
                jsonb(body.search.model_dump()),
                body.interval_seconds,
                body.enabled,
                actor,
            ),
        ).fetchone()


def run_watch(identifier: str, actor: str, *, key: str | None = None) -> dict[str, Any]:
    with transaction(write=True) as connection:
        row = connection.execute(
            "SELECT * FROM document_watches WHERE id=%s", (identifier,)
        ).fetchone()
        if row is None:
            raise ReviewError("Veille inconnue", 404)
        return submit(
            "search",
            {"watch_id": identifier, "search": row["definition"]},
            actor,
            dedup_key=f"manual:{identifier}:{key}" if key else None,
            connection=connection,
        )


def schedule_due(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    with transaction(write=True) as connection:
        rows = connection.execute(
            "SELECT * FROM document_watches WHERE enabled AND next_run<=%s FOR UPDATE",
            (now,),
        ).fetchall()
        for row in rows:
            slot = int(now.timestamp()) // row["interval_seconds"]
            submit(
                "search",
                {"watch_id": str(row["id"]), "search": row["definition"]},
                row["actor"],
                dedup_key=f"scheduled:{row['id']}:{slot}",
                connection=connection,
            )
            connection.execute(
                "UPDATE document_watches SET next_run=%s WHERE id=%s",
                (
                    now + timedelta(seconds=row["interval_seconds"]),
                    row["id"],
                ),
            )
        return len(rows)


def document(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM scientific_documents WHERE id=%s", (identifier,)
        ).fetchone()
        if row and row["merged_into"]:
            row = connection.execute(
                "SELECT * FROM scientific_documents WHERE id=%s", (row["merged_into"],)
            ).fetchone()
    if row is None:
        raise ReviewError("Document inconnu", 404)
    return row


def merge(connection: Any, keep: str, other: str) -> None:
    """Fusion sans effacer la provenance ni les décisions de l'ancienne identité."""
    if str(keep) == str(other):
        return
    rows = connection.execute(
        "SELECT * FROM scientific_documents WHERE id=ANY(%s::uuid[])",
        ([keep, other],),
    ).fetchall()
    dois = {r["doi"] for r in rows if r["doi"]}
    if len(dois) > 1:
        raise ReviewError("Identifiants contradictoires : deux DOI distincts ; revue nécessaire")
    source = next(r for r in rows if str(r["id"]) == str(other))
    target = next(r for r in rows if str(r["id"]) == str(keep))
    copies = target["metadata"].get("fulltexts", [])
    copies += [c for c in source["metadata"].get("fulltexts", []) if c not in copies]
    connection.execute(
        "UPDATE scientific_documents SET doi=NULL,merged_into=%s WHERE id=%s", (keep, other)
    )
    connection.execute(
        """UPDATE scientific_documents SET doi=coalesce(doi,%s),
        relevance=CASE WHEN %s='rejected' THEN 'rejected' ELSE relevance END,
        quality=CASE WHEN %s='rejected' THEN 'rejected' ELSE quality END,
        updated_at=now() WHERE id=%s""",
        (source["doi"], source["relevance"], source["quality"], keep),
    )
    connection.execute(
        """UPDATE scientific_documents SET identifiers=%s,metadata=%s,
        authors=CASE WHEN authors='[]'::jsonb THEN %s ELSE authors END,
        published_date=coalesce(published_date,%s),abstract=coalesce(abstract,%s),
        url=coalesce(url,%s),license=coalesce(license,%s) WHERE id=%s""",
        (
            jsonb({**source["identifiers"], **target["identifiers"]}),
            jsonb({**source["metadata"], **target["metadata"], "fulltexts": copies}),
            jsonb(source["authors"]),
            source["published_date"],
            source["abstract"],
            source["url"],
            source["license"],
            keep,
        ),
    )
    for table in (
        "document_identifiers",
        "document_provenance",
        "document_assets",
        "document_reviews",
    ):
        connection.execute(f"UPDATE {table} SET document_id=%s WHERE document_id=%s", (keep, other))
    connection.execute(
        """INSERT INTO document_watch_matches(watch_id,document_id)
        SELECT watch_id,%s FROM document_watch_matches WHERE document_id=%s
        ON CONFLICT DO NOTHING""",
        (keep, other),
    )
    connection.execute("DELETE FROM document_watch_matches WHERE document_id=%s", (other,))
    connection.execute(
        """INSERT INTO document_species(document_id,species,enabled,origin,actor,updated_at)
      SELECT %s,species,enabled,origin,actor,updated_at FROM document_species WHERE document_id=%s
      ON CONFLICT(document_id,species) DO UPDATE SET
        enabled=excluded.enabled,origin=excluded.origin,actor=excluded.actor,updated_at=excluded.updated_at
      WHERE excluded.origin='human' AND (document_species.origin='discovery'
        OR excluded.updated_at>document_species.updated_at)""",
        (keep, other),
    )
    connection.execute("DELETE FROM document_species WHERE document_id=%s", (other,))
    connection.execute(
        "UPDATE document_selection_history SET document_id=%s WHERE document_id=%s", (keep, other)
    )
    connection.execute(
        "UPDATE scientific_documents SET merged_into=%s WHERE merged_into=%s", (keep, other)
    )
    connection.execute(
        """UPDATE scientific_documents SET processing_status=CASE
        WHEN EXISTS(SELECT 1 FROM document_assets a JOIN document_chunks c ON c.asset_id=a.id
                    WHERE a.document_id=%s) THEN 'indexed'
        WHEN EXISTS(SELECT 1 FROM document_assets WHERE document_id=%s) THEN 'imported'
        ELSE processing_status END WHERE id=%s""",
        (keep, keep, keep),
    )


def register(publication: Publication, task_id: str, watch_id: str | None = None) -> str:
    ids = {**publication.identifiers, publication.source: publication.source_id}
    if publication.doi:
        ids["doi"] = publication.doi
    with transaction(write=True) as connection:
        found: set[str] = set()
        for namespace, value in ids.items():
            row = connection.execute(
                "SELECT document_id FROM document_identifiers WHERE namespace=%s AND value=%s",
                (namespace, value),
            ).fetchone()
            if row:
                found.add(str(row["document_id"]))
        if publication.doi:
            row = connection.execute(
                "SELECT id FROM scientific_documents WHERE doi=%s", (publication.doi,)
            ).fetchone()
            if row:
                found.add(str(row["id"]))
        if found:
            rows = connection.execute(
                "SELECT * FROM scientific_documents WHERE id=ANY(%s::uuid[]) "
                "ORDER BY created_at,id",
                (list(found),),
            ).fetchall()
            identifier = str(rows[0]["id"])
            for other in rows[1:]:
                merge(connection, identifier, str(other["id"]))
        else:
            identifier = str(uuid4())
            connection.execute(
                "INSERT INTO scientific_documents(id,title) VALUES(%s,%s)",
                (identifier, publication.title),
            )
        current = connection.execute(
            "SELECT * FROM scientific_documents WHERE id=%s", (identifier,)
        ).fetchone()
        if current["doi"] and publication.doi and current["doi"] != publication.doi:
            raise ReviewError("DOI contradictoires pour cette publication")
        metadata = current["metadata"]
        fulltexts = metadata.get("fulltexts", [])
        for candidate in publication.fulltexts:
            row = candidate.model_dump()
            if row not in fulltexts:
                fulltexts.append(row)
        connection.execute(
            """UPDATE scientific_documents SET doi=coalesce(doi,%s),
            authors=CASE WHEN authors='[]'::jsonb THEN %s ELSE authors END,
            published_date=coalesce(published_date,%s),abstract=coalesce(abstract,%s),
            url=coalesce(url,%s),license=coalesce(license,%s),
            identifiers=identifiers || %s,metadata=%s,updated_at=now() WHERE id=%s""",
            (
                publication.doi,
                jsonb(publication.authors),
                publication.published_date,
                publication.abstract,
                publication.url,
                publication.license,
                jsonb(ids),
                jsonb({**metadata, "fulltexts": fulltexts}),
                identifier,
            ),
        )
        for namespace, value in ids.items():
            connection.execute(
                """INSERT INTO document_identifiers(namespace,value,document_id)
                VALUES(%s,%s,%s) ON CONFLICT(namespace,value)
                DO UPDATE SET document_id=excluded.document_id""",
                (namespace, value, identifier),
            )
        raw = publication.model_dump(mode="json")
        connection.execute(
            """INSERT INTO document_provenance
            (document_id,source,source_id,snapshot_sha256,raw,task_id) VALUES(%s,%s,%s,%s,%s,%s)
            ON CONFLICT(source,source_id,snapshot_sha256) DO UPDATE SET observed_at=now()""",
            (
                identifier,
                publication.source,
                publication.source_id,
                hashlib.sha256(canonical(raw)).hexdigest(),
                jsonb(raw),
                task_id,
            ),
        )
        if watch_id:
            connection.execute(
                "INSERT INTO document_watch_matches VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (watch_id, identifier),
            )
    event(
        task_id,
        "discovery",
        "Métadonnées conservées",
        document=identifier,
        data={"source": publication.source, "source_id": publication.source_id},
    )
    return identifier


def review(identifier: str, body: Decision, actor: str) -> dict[str, Any]:
    identifier = str(document(identifier)["id"])
    with transaction(write=True) as connection:
        connection.execute(
            """INSERT INTO document_reviews(document_id,relevance,quality,note,actor)
            VALUES(%s,%s,%s,%s,%s)""",
            (identifier, body.relevance, body.quality, body.note, actor),
        )
        connection.execute(
            "UPDATE scientific_documents SET relevance=%s,quality=%s,updated_at=now() WHERE id=%s",
            (body.relevance, body.quality, identifier),
        )
    return document(identifier)
