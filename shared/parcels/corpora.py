"""One parcel, several original videos, immutable dossier membership snapshots."""

from typing import Any
from uuid import uuid4

from shared import console
from shared.access import actor_scope
from shared.analysis_settings import AnalysisOptions
from shared.parcels import service
from shared.parcels.schemas import Profile
from shared.review.database import ReviewError, jsonb, transaction


def create(video_ids: list[str], actor: str) -> dict[str, Any]:
    # Deduplicate physical originals, including console/review aliases, before scheduling GPU work.
    with transaction() as connection:
        rows = connection.execute(
            "SELECT * FROM (" + console.VIDEO_QUERY + ") v WHERE id=ANY(%s)",
            (list(dict.fromkeys(video_ids)),),
        ).fetchall()
    by_id = {r["id"]: r for r in rows}
    if set(video_ids) - by_id.keys():
        raise ReviewError("Une vidéo du corpus est introuvable", 404)
    videos = {by_id[i]["sha256"]: by_id[i] for i in dict.fromkeys(video_ids)}
    identifier = str(uuid4())
    with transaction(write=True) as connection:
        connection.execute(
            "INSERT INTO parcel_corpora(id,actor) VALUES(%s,%s)", (identifier, actor)
        )
        for ordinal, row in enumerate(videos.values()):
            connection.execute(
                """INSERT INTO parcel_corpus_videos
                (corpus_id,video_id,sha256,filename,ordinal) VALUES(%s,%s,%s,%s,%s)""",
                (identifier, row["id"], row["sha256"], row["filename"], ordinal),
            )
    return read(identifier)


def listing() -> list[dict[str, Any]]:
    with transaction() as connection:
        return connection.execute(
            """SELECT c.*,count(v.video_id) AS video_count,
            (SELECT id FROM parcel_dossiers d WHERE d.corpus_id=c.id
             ORDER BY created_at DESC LIMIT 1) AS latest_dossier_id
            FROM parcel_corpora c JOIN parcel_corpus_videos v ON v.corpus_id=c.id
            WHERE (%s::text IS NULL OR c.actor=%s)
            GROUP BY c.id ORDER BY c.created_at DESC LIMIT 100""",
            (actor_scope(), actor_scope()),
        ).fetchall()


def read(identifier: str) -> dict[str, Any]:
    with transaction() as connection:
        corpus = connection.execute(
            "SELECT * FROM parcel_corpora WHERE id=%s", (identifier,)
        ).fetchone()
        if not corpus:
            raise ReviewError("Groupe de vidéos introuvable", 404)
        videos = connection.execute(
            """SELECT * FROM parcel_corpus_videos
            WHERE corpus_id=%s ORDER BY ordinal""",
            (identifier,),
        ).fetchall()
        profile = connection.execute(
            """SELECT * FROM parcel_corpus_profiles
            WHERE corpus_id=%s ORDER BY revision DESC LIMIT 1""",
            (identifier,),
        ).fetchone()
        latest = connection.execute(
            """SELECT id FROM parcel_dossiers WHERE corpus_id=%s
            ORDER BY created_at DESC LIMIT 1""",
            (identifier,),
        ).fetchone()
    return {
        **corpus,
        "videos": videos,
        "profile": profile,
        "dossier": service.dossier(str(latest["id"])) if latest else None,
    }


def save(identifier: str, body: Profile, actor: str) -> dict[str, Any]:
    read(identifier)
    data = body.model_dump(exclude={"expected_revision"})
    with transaction(write=True) as connection:
        current = connection.execute(
            """SELECT * FROM parcel_corpus_profiles
            WHERE corpus_id=%s ORDER BY revision DESC LIMIT 1""",
            (identifier,),
        ).fetchone()
        revision = current["revision"] if current else 0
        if revision != body.expected_revision:
            raise ReviewError("La parcelle a été modifiée ailleurs. Rechargez le formulaire.", 409)
        if current and current["profile"] == data:
            return current
        return connection.execute(
            """INSERT INTO parcel_corpus_profiles
            (corpus_id,revision,profile,actor) VALUES(%s,%s,%s,%s) RETURNING *""",
            (identifier, revision + 1, jsonb(data), actor),
        ).fetchone()


def _analysis(connection: Any, video_id: str, actor: str) -> str:
    # Successful results are preferred; unfinished analyses are reused; errors are retried.
    existing = connection.execute(
        """SELECT id FROM console_tasks WHERE kind='analysis'
        AND request->>'video_id'=%s AND status IN ('completed','queued','running')
        AND NOT cancel_requested AND (%s::text IS NULL OR actor=%s)
        ORDER BY (status='completed') DESC,created_at DESC LIMIT 1""",
        (video_id, actor_scope(), actor_scope()),
    ).fetchone()
    if existing:
        return str(existing["id"])
    video = console.video(video_id)
    model = connection.execute("""SELECT id,checkpoint_key,sha256,family,
        version,preprocessing_version FROM console_models WHERE active""").fetchone()
    options = AnalysisOptions(detection_only=model is None)
    payload = {
        **options.model_dump(mode="json", exclude={"parcel_revision", "shadow_model_id"}),
        "video_id": video_id,
        "video_key": video["video_key"],
    }
    if model:
        payload["model"] = {**model, "id": str(model["id"])}
    return console.submit("analysis", payload, actor, connection)["id"]


def request(identifier: str, revision: int, actor: str) -> dict[str, Any]:
    corpus = read(identifier)
    with transaction(write=True) as connection:
        if not connection.execute(
            """SELECT 1 FROM parcel_corpus_profiles
            WHERE corpus_id=%s AND revision=%s""",
            (identifier, revision),
        ).fetchone():
            raise ReviewError("Version du formulaire inconnue", 422)
        existing = connection.execute(
            """SELECT id FROM parcel_dossiers d WHERE corpus_id=%s
            AND profile_revision=%s AND status IN ('waiting_analysis','queued')
            AND NOT EXISTS(SELECT 1 FROM document_tasks t WHERE t.id=d.task_id
                           AND t.status IN ('error','partial','completed'))
            ORDER BY created_at DESC LIMIT 1""",
            (identifier, revision),
        ).fetchone()
        if existing:
            return {"id": str(existing["id"]), "status": "queued"}
        entries = [(row, _analysis(connection, row["video_id"], actor)) for row in corpus["videos"]]
        dossier_id = str(uuid4())
        connection.execute(
            """INSERT INTO parcel_dossiers
            (id,corpus_id,profile_revision,analysis_id,actor) VALUES(%s,%s,%s,%s,%s)""",
            (dossier_id, identifier, revision, entries[0][1], actor),
        )
        for row, analysis_id in entries:
            connection.execute(
                """INSERT INTO parcel_dossier_videos
                (dossier_id,video_id,sha256,filename,ordinal,analysis_id)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (
                    dossier_id,
                    row["video_id"],
                    row["sha256"],
                    row["filename"],
                    row["ordinal"],
                    analysis_id,
                ),
            )
    return {"id": dossier_id, "status": "waiting_analysis"}
