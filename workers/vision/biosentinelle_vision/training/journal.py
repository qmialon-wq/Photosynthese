import logging
from typing import Any

from ..storage import LocalStorage


def publish(
    storage: LocalStorage, metadata: dict[str, Any], events: list[dict[str, Any]], database: bool
) -> None:
    storage.write_json("run.json", metadata)
    storage.write_json("history.json", events)
    if database:
        try:
            from shared.training_metrics import project_run

            project_run(metadata, events)
            storage.write_json("database_sync.json", {"status": "ok"})
        except Exception:
            # PostgreSQL peut être indisponible sans perdre le checkpoint ni les métriques.
            logging.getLogger(__name__).exception(
                "Métriques PostgreSQL non synchronisées ; JSON conservés"
            )
            storage.write_json("database_sync.json", {"status": "pending", "retry": "metrics-sync"})
