"""Territorial input revisions. No external call takes place in an HTTP request."""

import json
from typing import Any

from shared.access import actor_scope
from shared.parcels.service import snapshot_sha
from shared.parcels.territorial_schemas import Location, TerritorialRequest
from shared.rag import service as rag
from shared.review.database import ReviewError, transaction


def owned(connection: Any, identifier: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM parcel_corpora WHERE id=%s AND (%s::text IS NULL OR actor=%s)",
        (identifier, actor_scope(), actor_scope()),
    ).fetchone()
    if not row:
        raise ReviewError("Dossier introuvable", 404)
    return row


def location(connection: Any, identifier: str) -> dict[str, Any] | None:
    return connection.execute(
        "SELECT * FROM parcel_locations WHERE corpus_id=%s ORDER BY revision DESC LIMIT 1",
        (identifier,),
    ).fetchone()


def save_location(identifier: str, body: Location, actor: str) -> dict[str, Any]:
    with transaction(write=True) as c:
        owned(c, identifier)
        previous = location(c, identifier)
        revision = previous["revision"] if previous else 0
        if revision != body.expected_revision:
            raise ReviewError("La localisation a changé. Rechargez avant d'enregistrer.", 409)
        if previous and all(
            previous[k] == getattr(body, k) for k in ("latitude", "longitude", "provenance")
        ):
            return previous
        return c.execute(
            """INSERT INTO parcel_locations
            (corpus_id,revision,latitude,longitude,provenance,actor)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING *""",
            (identifier, revision + 1, body.latitude, body.longitude, body.provenance, actor),
        ).fetchone()


def inputs(c: Any, identifier: str) -> dict[str, Any]:
    owned(c, identifier)
    profile = c.execute(
        "SELECT * FROM parcel_corpus_profiles WHERE corpus_id=%s ORDER BY revision DESC LIMIT 1",
        (identifier,),
    ).fetchone()
    videos = c.execute(
        "SELECT video_id,sha256 FROM parcel_corpus_videos WHERE corpus_id=%s ORDER BY ordinal",
        (identifier,),
    ).fetchall()
    # Both aliases identify the same physical original; predictions are never used here.
    observations = rag.observations(
        sorted({v[k] for v in videos for k in ("video_id", "sha256")}), []
    )
    return json.loads(
        json.dumps(
            {
                "location": location(c, identifier),
                "profile": profile["profile"] if profile else {},
                "profile_revision": profile["revision"] if profile else 0,
                "observations": observations,
            },
            default=str,
            ensure_ascii=False,
        )
    )


def request(identifier: str, body: TerritorialRequest, actor: str) -> dict[str, Any]:
    from uuid import uuid4

    from shared.documents import service as documents
    from shared.review.database import jsonb

    with transaction(write=True) as c:
        snapshot = inputs(c, identifier)
        if not snapshot["location"]:
            raise ReviewError("Enregistrez un point avant de consulter IGN", 422)
        if (
            snapshot["location"]["revision"] != body.expected_location_revision
            or snapshot["profile_revision"] != body.expected_profile_revision
        ):
            raise ReviewError("Les entrées ont changé. Rechargez le dossier.", 409)
        digest = snapshot_sha(snapshot)
        previous = c.execute(
            "SELECT q.*,t.status AS task_status FROM territorial_queries q "
            "LEFT JOIN document_tasks t ON t.id=q.task_id "
            "WHERE corpus_id=%s ORDER BY revision DESC LIMIT 1",
            (identifier,),
        ).fetchone()
        if (
            previous
            and previous["input_sha256"] == digest
            and previous["task_status"] in ("queued", "running")
        ):
            return {"id": str(previous["id"]), "status": "pending"}
        query_id = str(uuid4())
        revision = previous["revision"] + 1 if previous else 1
        task = documents.submit(
            "territorial",
            {"query_id": query_id},
            actor,
            dedup_key=f"territorial:{query_id}",
            connection=c,
        )
        c.execute(
            "INSERT INTO territorial_queries "
            "(id,corpus_id,revision,input_sha256,inputs,task_id,actor) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (query_id, identifier, revision, digest, jsonb(snapshot), task["id"], actor),
        )
        return {"id": query_id, "status": "pending"}


def context(
    identifier: str, revision: int | None = None, *, include_archives: bool = False
) -> dict[str, Any]:
    with transaction() as c:
        current = inputs(c, identifier)
        row = c.execute(
            "SELECT q.*,t.status AS task_status,t.error AS task_error FROM territorial_queries q "
            "LEFT JOIN document_tasks t ON t.id=q.task_id WHERE corpus_id=%s "
            "AND (%s::int IS NULL OR revision=%s) ORDER BY revision DESC LIMIT 1",
            (identifier, revision, revision),
        ).fetchone()
    if revision is not None and not row:
        raise ReviewError("Révision territoriale inconnue", 404)
    if row:
        with transaction() as c:
            documentary = c.execute(
                "SELECT status,error,result FROM document_tasks "
                "WHERE kind='territorial_evidence' AND request->>'query_id'=%s "
                "ORDER BY created_at DESC LIMIT 1",
                (str(row["id"]),),
            ).fetchone()
        row["documentary_task"] = documentary
        row["obsolete"] = row["input_sha256"] != snapshot_sha(current)
        ok = sum(r["status"] in ("success", "empty") for r in row["layers"].values())
        row["status"] = (
            ("complete" if ok == 4 else "partial" if ok else "failed")
            if row["result"]
            else ("failed" if row["task_status"] == "error" else "pending")
        )
    if row and not include_archives:
        # The UI polls a compact view. Exact responses remain in SQL and in the export.
        row["layers"] = {
            name: {
                **{k: v for k, v in layer.items() if k not in ("raw_response", "features")},
                "archive_available": "raw_response" in layer,
                "features": [
                    {k: v for k, v in f.items() if k != "geometry"}
                    for f in layer.get("features", [])
                ],
            }
            for name, layer in row["layers"].items()
        }
    return {**current, "query": row}
