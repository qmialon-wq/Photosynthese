import os
import sys
import time

from redis import Redis

from shared.worker_runtime import heartbeat_is_fresh, heartbeat_key


def main() -> None:
    with Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    ) as client:
        value = client.get(heartbeat_key(sys.argv[1]))
    if not heartbeat_is_fresh(
        value, float(os.getenv("WORKER_HEARTBEAT_MAX_AGE_SECONDS", "30")), time.time()
    ):
        raise SystemExit("Worker sans signal de vie récent")


if __name__ == "__main__":
    main()
