"""Processus d'attente supervisé. Aucune file n'est consommée à cette étape."""

import logging
import os
import signal
import threading
import time

from redis import Redis

logger = logging.getLogger(__name__)


def heartbeat_key(role: str) -> str:
    return f"biosentinelle:worker:{role}:heartbeat"


def heartbeat_is_fresh(value: str | None, max_age: float, now: float) -> bool:
    try:
        age = now - float(value) if value is not None else -1
    except ValueError:
        return False
    return 0 <= age <= max_age


def run(role: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    interval = float(os.getenv("WORKER_HEARTBEAT_SECONDS", "5"))
    max_age = float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30"))
    if interval <= 0 or max_age <= interval * 2:
        raise ValueError("Le délai maximal doit dépasser deux intervalles strictement positifs")
    stop = threading.Event()

    def shutdown(signum: int, frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    client = Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    logger.info("Worker %s en attente ; aucun traitement implémenté", role)
    try:
        while not stop.is_set():
            client.set(heartbeat_key(role), str(time.time()), ex=int(max_age) + 1)
            stop.wait(interval)
    finally:
        client.delete(heartbeat_key(role))
        client.close()
