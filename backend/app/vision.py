import os
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from redis.exceptions import RedisError

from shared.vision_jobs import AnalysisRequest, JobStore

router = APIRouter(prefix="/vision", tags=["vision"])
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


@router.post("/analyses", status_code=202)
def submit_analysis(body: AnalysisRequest, request: Request) -> dict[str, Any]:
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "datasets/inbox").resolve()
    video = (root / body.video).resolve()
    if not video.is_relative_to(root) or video.suffix.lower() not in VIDEO_EXTENSIONS:
        raise HTTPException(422, "Vidéo hors inbox ou extension non prise en charge")
    if not video.is_file():
        raise HTTPException(404, "Vidéo absente de data/datasets/inbox")
    try:
        job = JobStore(request.app.state.redis).enqueue(body)
    except RedisError as exc:
        raise HTTPException(503, "File de tâches indisponible") from exc
    return {**job, "status_url": f"/vision/analyses/{job['id']}"}


@router.get("/analyses/{job_id}")
def analysis_status(job_id: UUID, request: Request) -> dict[str, Any]:
    try:
        job = JobStore(request.app.state.redis).get(str(job_id))
    except RedisError as exc:
        raise HTTPException(503, "File de tâches indisponible") from exc
    if job is None:
        raise HTTPException(404, "Analyse inconnue")
    return job


@router.get("/analyses/{job_id}/artifacts/{artifact}")
def analysis_artifact(
    job_id: UUID,
    artifact: Literal["video", "report", "statistics"],
    request: Request,
) -> FileResponse:
    job = analysis_status(job_id, request)
    if job.get("kind", "analysis") != "analysis":
        raise HTTPException(404, "Les métriques de ce run sont sous /training/runs")
    if job["status"] != "completed":
        raise HTTPException(409, "Analyse non terminée avec succès")
    root = (Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/vision").resolve()
    names = {"video": "annotated.mp4", "report": "report.json", "statistics": "statistics.json"}
    target = (root / job["result"]["output"] / names[artifact]).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404, "Artefact absent")
    return FileResponse(
        target, media_type="video/mp4" if artifact == "video" else "application/json"
    )
