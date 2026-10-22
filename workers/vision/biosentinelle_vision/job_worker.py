"""Consommateur unique, tâches durables et reprise des messages non acquittés."""

import logging
import os
import signal
import threading
import time
from datetime import UTC, datetime
from typing import Any

from redis import Redis
from redis.exceptions import ResponseError

from shared.vision_jobs import CONSUMER, GROUP, STREAM, AnalysisRequest, JobStore, TrainingRequest
from shared.worker_runtime import heartbeat_key

from .classes import ClassManifest, load_classes
from .commands import input_videos, run_analyses
from .config import VisionSettings
from .errors import GpuBusyError, TrainingInterrupted, VisionError
from .storage import LocalStorage

logger = logging.getLogger(__name__)


def execute_job(
    job: dict[str, Any],
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event | None = None,
) -> dict[str, Any]:
    if job.get("kind") == "console":
        from shared.vision_jobs import ConsoleRequest

        from .console_tasks import execute

        return execute(
            ConsoleRequest.model_validate(job["request"]).task_id, settings, classes, stop
        )
    if job.get("kind") == "review":
        from shared.vision_jobs import ReviewRequest

        from .review.operations import execute_operation

        review = ReviewRequest.model_validate(job["request"])
        return execute_operation(review.operation_id, settings, classes)
    if job.get("kind") in ("train_classifier", "evaluate_classifier"):
        from .commands import train_from_manifest

        request = TrainingRequest.model_validate(job["request"])
        config = VisionSettings.model_validate(request.configuration)
        # Le matériel est choisi par le worker déployé, pas par le client de soumission.
        config.device = settings.device
        if request.kind == "evaluate_classifier":
            from .training.commands import evaluate_classifier

            return {
                "status": "completed",
                "metrics": evaluate_classifier(config, classes, request.split),
            }
        if not config.training.run_id:
            config.training.run_id = job["id"]
        last = config.checkpoint_root / config.training.run_id / "last.pt"
        if config.training.resume_checkpoint is None and last.is_file():
            config.training.resume_checkpoint = last
        result = train_from_manifest(config, classes, stop)
        if result.get("status") == "completed" and config.training.register_model_name:
            from .console_tasks import register_model

            registered = register_model(
                {
                    "checkpoint_key": str(
                        config.checkpoint_root.joinpath(
                            config.training.run_id, "best.pt"
                        ).relative_to(settings.checkpoint_root)
                    ),
                    "name": config.training.register_model_name,
                },
                "training-worker",
                settings,
                classes,
                stop,
            )
            result.update(registered)
            if config.training.activate_on_success:
                result["activation"] = {
                    "active": False,
                    "reason": "Comparaison et promotion requises",
                }
            LocalStorage(config.output_root).write_json(
                f"training/{config.training.run_id}/registration.json",
                registered | {"activation": result.get("activation")},
            )
        return result
    request = AnalysisRequest.model_validate(job["request"])
    updates = request.model_dump(exclude={"video", "track_threshold", "track_min_hits", "force"})
    updates.update(analysis_video=request.video, analysis_force=request.force)
    config = VisionSettings.model_validate(
        {
            **settings.model_dump(),
            **updates,
            "tracking": {
                **settings.tracking.model_dump(),
                "confidence_threshold": request.track_threshold,
                "min_hits": request.track_min_hits,
            },
        }
    )
    results = run_analyses(input_videos(config), config, classes)
    if len(results) != 1:
        raise VisionError("Une tâche doit traiter exactement une vidéo locale")
    return results[0]


def consume_one(
    client: Redis,
    settings: VisionSettings,
    classes: ClassManifest,
    stop: threading.Event | None = None,
) -> bool:
    # Nom stable : reprise des tâches interrompues au redémarrage.
    messages = client.xreadgroup(GROUP, CONSUMER, {STREAM: "0"}, count=1)
    if not messages or not messages[0][1]:
        messages = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=1000)
    if not messages or not messages[0][1]:
        return False
    message_id, fields = messages[0][1][0]
    store = JobStore(client)
    job = store.get(fields["id"])
    if job is None:
        raise VisionError(f"État de tâche absent pour le message {message_id}")
    if job["status"] in ("completed", "error"):
        store.finish(message_id, job)
        return True
    job.update(status="running", started_at=datetime.now(UTC).isoformat())
    store.save(job)
    try:
        result = execute_job(job, settings, classes, stop)
        job.update(status=result["status"], result=result)
    except (GpuBusyError, TrainingInterrupted):
        job["status"] = "queued"
        store.save(job)
        return False
    except Exception as exc:
        logger.exception("Échec de la tâche %s", job["id"])
        job.update(status="error", error=f"{type(exc).__name__}: {exc}")
    job["finished_at"] = datetime.now(UTC).isoformat()
    store.finish(message_id, job)
    return True


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = VisionSettings()
    classes = load_classes(settings.classes_manifest)
    stop, lost_lease = threading.Event(), threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    client = Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=5,
    )
    lease = client.lock("biosentinelle:vision:consumer-lock", timeout=30, thread_local=False)
    if not lease.acquire(blocking=False):
        raise VisionError("Un consommateur vision est déjà actif")
    interval = float(os.getenv("WORKER_HEARTBEAT_SECONDS", "5"))
    max_age = float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30"))
    if not 0 < interval < min(10, max_age / 2):
        lease.release()
        raise VisionError("Intervalle heartbeat invalide pour le bail du consommateur")

    def keep_alive() -> None:
        while not stop.is_set():
            try:
                lease.extend(30, replace_ttl=True)
                client.set(heartbeat_key("vision"), str(time.time()), ex=int(max_age) + 1)
            except Exception:
                logger.exception("Perte du bail Redis ; arrêt après la tâche courante")
                lost_lease.set()
                stop.set()
            stop.wait(interval)

    heartbeat = threading.Thread(target=keep_alive, daemon=True)
    try:
        try:
            client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        heartbeat.start()
        logger.info("Consommateur vision prêt ; aucun modèle chargé avant une tâche")
        while not stop.is_set():
            from shared.console import publish_pending as publish_console
            from shared.review.outbox import publish_pending

            try:
                publish_pending(client)
                publish_console(client)
            except Exception:
                logger.exception(
                    "Publication de l'outbox de revue impossible ; nouvel essai au prochain tour"
                )
            if not consume_one(client, settings, classes, stop):
                stop.wait(1)
        if lost_lease.is_set():
            raise VisionError("Bail Redis perdu")
    finally:
        stop.set()
        if heartbeat.is_alive():
            heartbeat.join(timeout=6)
        if lease.owned():
            client.delete(heartbeat_key("vision"))
            lease.release()
        client.close()
