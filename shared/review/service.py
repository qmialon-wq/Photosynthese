from typing import Any
from uuid import uuid4

from shared.access import video_ids

from .database import ReviewError, jsonb, transaction
from .schemas import BatchDecision, Decision

SAMPLE_QUERY = """
 SELECT s.id,s.frame_id,s.original_box,s.original_crop_key,s.detector_identity,
 s.detection_score,s.predicted_label,s.classification_score,s.probabilities,
 f.image_key AS original_image_key,f.sha256 AS original_sha256,f.width,f.height,
 f.frame_index,f.time_seconds,
 f.quality || jsonb_build_object('near_duplicate', EXISTS(
   SELECT 1 FROM review_similarities pair WHERE pair.first_id=f.id OR pair.second_id=f.id
 )) AS frame_quality,
 v.id AS video_id,v.group_id,v.source_key,v.original_name,v.species_candidate,
 v.status AS video_status,g.split,g.test_locked,
 r.revision,r.state,r.label,r.box,r.recipe,r.crop_key,r.crop_sha256,r.quality,
 r.render_status,r.actor,r.provenance,r.created_at
 FROM review_samples s JOIN review_frames f ON f.id=s.frame_id
 JOIN review_videos v ON v.id=f.video_id JOIN review_groups g ON g.id=v.group_id
 JOIN review_revisions r ON r.sample_id=s.id AND r.revision=s.current_revision
"""


def operation(connection: Any, kind: str, payload: dict[str, Any], actor: str) -> str:
    identifier = str(uuid4())
    connection.execute(
        "INSERT INTO review_operations(id,kind,payload,actor) VALUES(%s,%s,%s,%s)",
        (identifier, kind, jsonb(payload), actor),
    )
    return identifier


def submit(kind: str, payload: dict[str, Any], actor: str) -> dict[str, Any]:
    with transaction(write=True) as connection:
        identifier = operation(connection, kind, payload, actor)
    return {"id": identifier, "status": "queued", "status_url": f"/review/operations/{identifier}"}


def get_operation(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM review_operations WHERE id=%s", (identifier,)
        ).fetchone()
    if row is None:
        raise ReviewError("Opération inconnue", 404)
    return row


def get_sample(identifier: str, connection: Any = None) -> dict[str, Any]:
    if connection is None:
        with transaction() as current:
            return get_sample(identifier, current)
    row = connection.execute(SAMPLE_QUERY + " WHERE s.id=%s", (identifier,)).fetchone()
    if row is None:
        raise ReviewError("Recadrage inconnu", 404)
    return row


def history(identifier: str) -> list[dict[str, Any]]:
    with transaction() as connection:
        get_sample(identifier, connection)
        return connection.execute(
            "SELECT * FROM review_revisions WHERE sample_id=%s ORDER BY revision", (identifier,)
        ).fetchall()


def decide(
    identifier: str, decision: Decision, actor: str, connection: Any = None
) -> dict[str, Any]:
    if connection is None:
        with transaction(write=True) as current:
            return decide(identifier, decision, actor, current)
    row = get_sample(identifier, connection)
    if row["video_status"] != "ready":
        raise ReviewError("Attendre la fin de l'import vidéo avant de valider")
    if row["test_locked"]:
        raise ReviewError("Ce groupe test est gelé dans un dataset versionné")
    if row["revision"] != decision.expected_revision:
        raise ReviewError("Révision obsolète ; relire le recadrage avant de corriger")
    label = None
    box = decision.box.model_dump() if decision.box else row["box"]
    state = "rejected" if decision.decision == "reject" else "pending"
    if decision.decision == "validate":
        label = decision.label or row["label"]
        if (
            label is None
            or not connection.execute(
                "SELECT 1 FROM review_species WHERE name=%s", (label,)
            ).fetchone()
        ):
            raise ReviewError("Choisir explicitement une espèce du manifeste", 422)
        baseline = row["predicted_label"] or row["species_candidate"]
        changed = (
            box != row["original_box"]
            or (baseline is not None and label != baseline)
            or (row["label"] is not None and label != row["label"])
            or row["state"] == "corrected"
        )
        state = "corrected" if changed else "validated"
    revision = row["revision"] + 1
    render = box != row["box"] or row["crop_key"] is None
    provenance = {
        "channel": "api",
        "reason": decision.reason.strip()
        or {
            "validate": "Validation humaine",
            "reject": "Rejet manuel",
            "reopen": "Remise en revue",
        }[decision.decision],
        "reason_source": "user" if decision.reason.strip() else "automatic",
        "parent_revision": row["revision"],
        "supplied": decision.provenance,
        "label_source": "human" if label else None,
    }
    connection.execute(
        """INSERT INTO review_revisions(sample_id,revision,state,label,box,recipe,
        crop_key,crop_sha256,quality,render_status,actor,provenance)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            identifier,
            revision,
            state,
            label,
            jsonb(box),
            jsonb(row["recipe"]),
            None if render else row["crop_key"],
            None if render else row["crop_sha256"],
            None if render else jsonb(row["quality"]),
            "pending" if render else row["render_status"],
            actor,
            jsonb(provenance),
        ),
    )
    connection.execute(
        "UPDATE review_samples SET current_revision=%s WHERE id=%s", (revision, identifier)
    )
    render_id = (
        operation(connection, "render_crop", {"sample_id": identifier, "revision": revision}, actor)
        if render
        else None
    )
    return {**get_sample(identifier, connection), "render_operation_id": render_id}


def list_samples(
    state: str | None,
    label: str | None,
    quality: str | None,
    limit: int,
    offset: int,
    video_id: str | None = None,
) -> list[dict[str, Any]]:
    # La rareté utilise uniquement le train validé, sans exploiter les labels du test.
    query = (
        """WITH counts AS (
      SELECT r.label,count(*) AS n FROM review_samples s JOIN review_revisions r
      ON (r.sample_id=s.id AND r.revision=s.current_revision)
      JOIN review_frames f ON f.id=s.frame_id JOIN review_videos v ON v.id=f.video_id
      JOIN review_groups g ON g.id=v.group_id
      WHERE r.state IN ('validated','corrected') AND g.split='train' GROUP BY r.label
    ), samples AS ("""
        + SAMPLE_QUERY
        + """), ranked AS (
      SELECT samples.*,100.0/(1+coalesce(counts.n,0))
       +20*(1-coalesce(classification_score,0)) AS priority
      FROM samples LEFT JOIN counts ON
        counts.label=coalesce(samples.label,predicted_label,species_candidate)
    ) SELECT * FROM ranked WHERE (%s::text IS NULL OR state=%s)
     AND (%s::text IS NULL OR coalesce(label,predicted_label,species_candidate)=%s)
     AND (%s::text IS NULL OR quality->>%s='true' OR frame_quality->>%s='true')
     AND (%s::text IS NULL OR video_id=%s)
     AND (%s::text[] IS NULL OR video_id=ANY(%s))
     ORDER BY priority DESC,id LIMIT %s OFFSET %s"""
    )
    with transaction() as connection:
        return connection.execute(
            query,
            (
                state,
                state,
                label,
                label,
                quality,
                quality,
                quality,
                video_id,
                video_id,
                video_ids(connection),
                video_ids(connection),
                limit,
                offset,
            ),
        ).fetchall()


def list_videos(status: str | None, limit: int, offset: int) -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            (
                "SELECT v.*,g.split,g.test_locked FROM review_videos v JOIN review_groups g ON "
                "g.id=v.group_id "
                "WHERE (%s::text IS NULL OR v.status=%s) AND (%s::text[] IS NULL OR "
                "v.id=ANY(%s)) ORDER BY v.id LIMIT %s OFFSET %s"
            ),
            (status, status, video_ids(connection), video_ids(connection), limit, offset),
        ).fetchall()


def decide_batch(batch: BatchDecision, actor: str) -> list[dict[str, Any]]:
    # Une seule transaction : ni correction partielle ni perte de verrouillage test.
    with transaction(write=True) as connection:
        return [
            decide(
                item.sample_id,
                Decision(
                    expected_revision=item.expected_revision,
                    decision=batch.decision,
                    label=batch.label,
                    reason=batch.reason,
                    provenance={"action": "batch", "size": len(batch.items)},
                ),
                actor,
                connection,
            )
            for item in batch.items
        ]
