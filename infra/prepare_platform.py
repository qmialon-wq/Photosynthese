"""Explicit, resumable preparation; run inside a connected worker container."""

import argparse
import contextlib
import json
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4


class Preparation:
    def __init__(self, kind: str, *, root: Path | None = None) -> None:
        self.root = root or Path("/storage/results/platform-setup")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / f"{kind}.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {"jobs": {}}
        self.state["status"] = "running"
        self.save()

    def save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, default=str))
        temporary.replace(self.path)

    def job(
        self, name: str, submit: Callable, lookup: Callable, *, optional: bool = False
    ) -> dict[str, Any] | None:
        if name not in self.state["jobs"]:
            self.state["jobs"][name] = {"id": str(submit()["id"])}
            self.save()
        saved = self.state["jobs"][name]
        previous = None
        while True:
            task = lookup(saved["id"])
            status = task["status"]
            if status != previous:
                print(name, saved["id"], status, flush=True)
                saved.update(status=status, error=task.get("error"))
                self.save()
                previous = status
            if status in ("completed", "partial"):
                saved["result"] = task.get("result") or {}
                self.save()
                return saved["result"]
            if status in ("error", "failed", "cancelled"):
                if optional:
                    return None
                raise RuntimeError(f"{name}: {task.get('error')}")
            time.sleep(5)

    def documents(self) -> None:
        from shared.documents import service
        from shared.documents.config import DocumentSettings
        from shared.documents.schemas import Search
        from shared.rag import service as rag
        from workers.documents.http import SafeHTTP
        from workers.documents.translation import prepare_model

        self.job("rag-prepare", lambda: rag.submit("prepare", {}, "platform-setup"), service.task)
        http = SafeHTTP(DocumentSettings())
        try:
            prepare_model(DocumentSettings(), http)
        finally:
            http.close()
        self.state["translation_model"] = "verified"
        self.save()
        species = [
            "chevreuil",
            "sanglier",
            "buse",
            "pigeons",
            "martres",
            "renards",
            "blaireaux",
            "chouette",
            "geai",
            "faisans",
        ]
        # Submit every collection before waiting, so progress is visible in the application.
        for name in species:
            key = f"collect-{name}"
            if key not in self.state["jobs"]:
                body = Search(
                    species=[name],
                    limit_per_source=20,
                    download_fulltext=True,
                    focus="human_activities",
                )
                task = service.submit("search", {"search": body.model_dump()}, "platform-setup")
                self.state["jobs"][key] = {"id": str(task["id"])}
                self.save()
        for name in species:
            self.job(f"collect-{name}", lambda: None, service.task, optional=True)
        self.job(
            "rag-index",
            lambda: rag.submit("index", {"document_ids": []}, "platform-setup"),
            service.task,
        )
        self.state["source_validation"] = "Human review remains required for retrieval eligibility."

    def vision(self) -> None:
        from biosentinelle_vision.classification.pretrained import (
            PRETRAINED_MODELS,
            fetch_pretrained,
        )
        from biosentinelle_vision.training.campaign import run_campaign

        from shared import console
        from shared.review.database import transaction

        for architecture in PRETRAINED_MODELS:
            fetch_pretrained(architecture, Path("/storage/models/pretrained"))
            print("Pretrained verified:", architecture, flush=True)
        # Make the existing classifier available while the new models train.
        registered = self.job(
            "existing-model",
            lambda: console.submit(
                "register_model",
                {"name": "Classificateur V3 existant", "checkpoint_key": "classifier_v3_best.pt"},
                "platform-setup",
            ),
            console.task,
            optional=True,
        )
        if registered:
            with transaction() as connection:
                active = connection.execute("SELECT id FROM console_models WHERE active").fetchone()
            if not active:
                console.activate_model(registered["model_id"], "platform-setup")
        if "campaign_id" not in self.state:
            self.state["campaign_id"] = str(uuid4())
            self.save()
        identifier = self.state["campaign_id"]
        campaign_path = Path("/storage/results/vision/campaigns") / f"{identifier}.json"
        if not campaign_path.exists():
            campaign_path.parent.mkdir(parents=True, exist_ok=True)
            campaign_path.write_text(
                json.dumps(
                    {
                        "id": identifier,
                        "jobs": {},
                        "models": [],
                        "parameters": {
                            "device": "cuda",
                            "allow_weak_labels": True,
                            "epochs_head": 6,
                            "epochs_finetune": 18,
                            "batch_size": 2,
                            "accumulation_steps": 4,
                            "architectures": list(PRETRAINED_MODELS),
                        },
                    }
                )
            )
        campaign = run_campaign(
            Path("/storage/results/vision"),
            device="cuda",
            allow_weak_labels=True,
            resume=identifier,
        )
        self.state["campaign_id"] = campaign["id"]
        self.save()
        manifest = campaign["snapshot_key"]
        extracted = self.job(
            "embeddings-extract",
            lambda: console.submit(
                "embeddings_extract",
                {
                    "manifest_key": manifest,
                    "architecture": "tf_efficientnetv2_b0",
                    "batch_size": 2,
                    "allow_weak_labels": True,
                },
                "platform-setup",
            ),
            console.task,
        )
        index_key = Path(extracted["index"]).relative_to("/storage/results/vision").as_posix()
        for candidate in ("logistic", "knn", "linear_svm", "rbf_svm"):
            output_key = f"platform-setup/{campaign['id']}/{candidate}"
            trained = self.job(
                f"embeddings-{candidate}",
                lambda candidate=candidate, output_key=output_key: console.submit(
                    "embeddings_train",
                    {
                        "index_key": index_key,
                        "output_key": output_key,
                        "candidates": [candidate],
                        "allow_weak_validation": True,
                    },
                    "platform-setup",
                ),
                console.task,
                optional=True,
            )
            if trained:
                self.job(
                    f"register-{candidate}",
                    lambda candidate=candidate, output_key=output_key: console.submit(
                        "register_model",
                        {
                            "name": f"Embeddings {candidate}",
                            "checkpoint_key": f"{output_key}/model.json",
                        },
                        "platform-setup",
                    ),
                    console.task,
                )
        for method in ("kmeans", "hdbscan"):
            self.job(
                f"embeddings-cluster-{method}",
                lambda method=method: console.submit(
                    "embeddings_cluster",
                    {
                        "index_key": index_key,
                        "output_key": f"exploration/{campaign['id']}-{method}.json",
                        "clusters": 10,
                        "method": method,
                    },
                    "platform-setup",
                ),
                console.task,
                optional=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["vision", "documents"])
    kind = parser.parse_args().kind
    preparation = Preparation(kind)
    with (preparation.root / f"{kind}.log").open("a", buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            try:
                getattr(preparation, kind)()
                warnings = any(
                    job.get("status") in ("error", "failed", "cancelled", "partial")
                    for job in preparation.state["jobs"].values()
                )
                preparation.state["status"] = "completed_with_warnings" if warnings else "completed"
            except Exception as exc:
                preparation.state.update(status="error", error=str(exc))
                traceback.print_exc()
                raise
            finally:
                preparation.save()


if __name__ == "__main__":
    main()
