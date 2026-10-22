"""Client de campagne : prépare une fois, soumet et attend chaque tâche Redis."""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from shared import console
from shared.classification_jobs import Comparison, freeze_comparison

from ..classification.pretrained import PRETRAINED_MODELS
from ..config import TrainingConfig
from ..datasets.inventory import file_hash
from ..errors import ManifestError
from ..storage import LocalStorage

ARCHITECTURES = tuple(PRETRAINED_MODELS)


def wait_for_task(identifier: str) -> dict[str, Any]:
    previous = None
    while True:
        task = console.task(identifier)
        status = task["status"]
        if status != previous:
            print(f"{identifier} : {status}", flush=True)
            previous = status
        if status == "completed":
            return task["result"]
        if status in ("error", "cancelled"):
            raise ManifestError(f"Tâche {identifier} {status} : {task.get('error')}")
        time.sleep(3)


def run_campaign(
    root: Path,
    *,
    device: str,
    allow_weak_labels: bool,
    epochs_head: int = 6,
    epochs_finetune: int = 18,
    batch_size: int = 2,
    accumulation_steps: int = 4,
    resume: str | None = None,
) -> dict[str, Any]:
    config = TrainingConfig(
        epochs_head=epochs_head,
        epochs_finetune=epochs_finetune,
        batch_size=batch_size,
        accumulation_steps=accumulation_steps,
        initialization="pretrained",
    )
    identifier = str(UUID(resume)) if resume else str(uuid4())
    storage = LocalStorage(root)
    key = f"campaigns/{identifier}.json"
    parameters = {
        "device": device,
        "allow_weak_labels": allow_weak_labels,
        "epochs_head": config.epochs_head,
        "epochs_finetune": config.epochs_finetune,
        "batch_size": config.batch_size,
        "accumulation_steps": config.accumulation_steps,
        "architectures": list(ARCHITECTURES),
    }
    if resume:
        state = json.loads(storage.read_bytes(key))
        if state["parameters"] != parameters:
            raise ManifestError("Reprise : conserver les paramètres de la campagne d'origine")
    else:
        state = {"id": identifier, "parameters": parameters, "jobs": {}, "models": []}
        storage.write_json(key, state)
    print(f"Campagne {identifier} — état : {storage.path(key)}", flush=True)

    def job(name: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if name not in state["jobs"]:
            operation = console.submit(kind, payload, "local-campaign")
            state["jobs"][name] = operation["id"]
            storage.write_json(key, state)
        return wait_for_task(state["jobs"][name])

    prepared = job(
        "dataset",
        "classification_dataset",
        {
            "allow_weak_labels": allow_weak_labels,
            "cross_split_policy": "quarantine",
        },
    )
    if not prepared["counts"].get("train") or not prepared["counts"].get("val"):
        raise ManifestError(
            "Train ou validation vide. Compléter la validation humaine, ou autoriser explicitement "
            "les labels de noms avec BENCHMARK_WEAK_LABELS=1 pour un benchmark exploratoire."
        )
    manifest = Path(prepared["manifest"]).with_name("training.json").resolve()
    snapshot_key = manifest.relative_to(storage.root).as_posix()
    checksum = file_hash(manifest)
    if state.get("snapshot_sha256", checksum) != checksum:
        raise ManifestError("Le snapshot de campagne a été modifié depuis la préparation")
    state.update(snapshot_key=snapshot_key, snapshot_sha256=checksum)
    storage.write_json(key, state)
    models = []
    for architecture in ARCHITECTURES:
        # Chaque tâche ordinaire publie ses métriques SQL et enregistre son meilleur checkpoint.
        result = job(
            architecture,
            "training",
            {
                "dataset_id": "base",
                "snapshot_key": snapshot_key,
                "snapshot_sha256": checksum,
                "model_name": architecture,
                "initialization": "pretrained",
                "image_size": 224,
                "batch_size": config.batch_size,
                "accumulation_steps": config.accumulation_steps,
                "epochs_head": config.epochs_head,
                "epochs_finetune": config.epochs_finetune,
                "patience": config.patience,
                "amp": "auto" if device == "cuda" else "off",
            },
        )
        models.append(result["model_id"])
        state["models"] = models.copy()
        storage.write_json(key, state)
    if state.get("comparison"):
        return state
    payload = freeze_comparison(
        Comparison(
            manifest_key=snapshot_key,
            model_ids=models,
            split="val",
            batch_size=config.batch_size,
            allow_weak_labels=allow_weak_labels,
        )
    )
    state["comparison"] = job("benchmark", "classifiers_compare", payload)
    storage.write_json(key, state)
    print("Benchmark terminé — Administration → Évaluation → Benchmarks", flush=True)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    args = parser.parse_args()
    actual = os.getenv("BIOSENTINELLE_VISION_DEVICE", "cpu")
    if actual != args.device:
        parser.error("Le worker démarré n'utilise pas le device demandé ; relancer training-up")
    try:
        run_campaign(
            Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/vision",
            device=args.device,
            allow_weak_labels=os.getenv("BENCHMARK_WEAK_LABELS", "0") == "1",
            epochs_head=int(os.getenv("CAMPAIGN_EPOCHS_HEAD", "6")),
            epochs_finetune=int(os.getenv("CAMPAIGN_EPOCHS_FINETUNE", "18")),
            batch_size=int(os.getenv("CAMPAIGN_BATCH_SIZE", "2")),
            accumulation_steps=int(os.getenv("CAMPAIGN_ACCUMULATION_STEPS", "4")),
            resume=os.getenv("CAMPAIGN_ID") or None,
        )
    except KeyboardInterrupt:
        parser.exit(
            130, "Suivi interrompu ; la tâche soumise continue. Reprendre avec CAMPAIGN_ID.\n"
        )
    except (ManifestError, ValueError, OSError) as exc:
        parser.exit(1, f"Erreur de campagne : {exc}\n")


if __name__ == "__main__":
    main()
