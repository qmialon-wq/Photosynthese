import gc
import logging
import math
import os
import random
import re
import threading
from collections import Counter
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..classes import ClassManifest
from ..classification.model import create_model
from ..classification.preprocessing import build_transform
from ..config import VisionSettings
from ..datasets.inventory import file_hash
from ..errors import ManifestError, ModelError, TrainingInterrupted
from ..schemas import CropRecord
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from .dataset import CropsDataset, select_samples
from .evaluation import evaluate_loader, load_video_truth
from .journal import publish
from .reproducibility import identity, restore_rng, rng_state, versions
from .steps import amp_dtype, train_epoch

logger = logging.getLogger(__name__)
SUPPORTED_MODELS = {
    "convnext_tiny",
    "efficientnetv2_s",
    "tf_efficientnetv2_b0",
    "efficientnetv2_rw_t",
    "mobilenetv3_small_050",
    "resnet50",
}


def configure_trainable(model: Any, phase: str, epoch: int, every: int) -> None:
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.get_classifier().parameters():
        parameter.requires_grad = True
    if phase != "finetune":
        return
    stages = (
        list(model.stages)
        if hasattr(model, "stages")
        else (
            list(model.blocks)
            if hasattr(model, "blocks")
            else [
                getattr(model, name)
                for name in ("layer1", "layer2", "layer3", "layer4")
                if hasattr(model, name)
            ]
        )
    )
    count = 1 + epoch // every
    modules = [model] if not stages or count >= len(stages) else stages[-count:]
    for module in modules:
        for parameter in module.parameters():
            parameter.requires_grad = True


def seed_worker(worker_id: int) -> None:
    import numpy as np
    import torch

    seed = torch.initial_seed() % (2**32)
    random.seed(seed)
    np.random.seed(seed)


def cpu_state(value: Any) -> Any:
    import torch

    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: cpu_state(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(cpu_state(v) for v in value)
    return value


def save_checkpoint(storage: LocalStorage, key: str, state: dict[str, Any]) -> None:
    import torch

    buffer = BytesIO()
    torch.save(cpu_state(state), buffer)
    storage.write_bytes(key, buffer.getvalue())


def train(
    records: Sequence[CropRecord],
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
    *,
    initial_checkpoint: Path | None = None,
    stop: threading.Event | None = None,
) -> dict[str, Any]:
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        try:
            return _train(
                records, storage, classes, settings, initial_checkpoint, stop or threading.Event()
            )
        finally:
            gc.collect()
            if settings.device == "cuda":
                import torch

                torch.cuda.empty_cache()


def _train(
    records: Sequence[CropRecord],
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
    initial_checkpoint: Path | None,
    stop: threading.Event,
) -> dict[str, Any]:
    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, WeightedRandomSampler

    config = settings.training
    if config.model_name not in SUPPORTED_MODELS:
        raise ModelError(f"Backbone non pris en charge : {config.model_name}")
    if config.resume_checkpoint and initial_checkpoint:
        raise ModelError("Choisir une reprise complète ou un checkpoint initial de poids")
    selected = select_samples(
        records,
        classes,
        settings.crops.max_per_video,
        allow_filename_labels=config.allow_filename_labels,
    )
    train_records = [r for r in selected if r.frame.split == "train"]
    val_records = [r for r in selected if r.frame.split == "val"]
    missing = set(classes.names) - {r.label for r in train_records}
    if not train_records or not val_records:
        raise ManifestError(f"Validation vide ou classes sans train validé : {sorted(missing)}")
    if settings.device == "cuda" and not torch.cuda.is_available():
        raise ModelError("CUDA demandé mais indisponible")
    if settings.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(settings.seed)
    np.random.seed(settings.seed)
    torch.manual_seed(settings.seed)
    torch.use_deterministic_algorithms(config.deterministic)
    torch.backends.cudnn.benchmark = not config.deterministic
    torch.backends.cudnn.deterministic = config.deterministic
    dtype = amp_dtype(settings.device, config.amp)
    truth = load_video_truth(config.video_truth_manifest, classes)
    resume = None
    if config.resume_checkpoint:
        resume = torch.load(config.resume_checkpoint, map_location="cpu", weights_only=True)
        classes.check_checkpoint(resume)
        if "initialization" not in resume.get("configuration", {}).get("training", {}):
            config.initialization = "legacy"
    signature = identity(selected, storage, classes, settings)
    if not resume and config.initialization == "legacy":
        raise ModelError("L'initialisation legacy est réservée à une reprise historique")
    if resume:
        if resume.get("training_schema") != "2" or resume.get("fingerprint") != signature:
            raise ManifestError(
                "Reprise incompatible : configuration, images, labels ou manifestes modifiés"
            )
        if config.run_id and resume["run_id"] != config.run_id:
            raise ManifestError("Identifiant de run incompatible avec la reprise")
    run_id = resume["run_id"] if resume else config.run_id or str(uuid4())
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", run_id):
        raise ManifestError("Identifiant de run invalide dans le checkpoint")
    config.run_id = run_id
    checkpoints = LocalStorage(settings.checkpoint_root / run_id)
    journal = LocalStorage(storage.root / "training" / run_id)
    if not resume and checkpoints.path("last.pt").exists():
        raise ModelError("Ce run existe déjà ; utiliser son checkpoint last.pt avec --resume")
    provenance = {
        "label_policy": "filename_provisional" if config.allow_filename_labels else "human_only",
        "train_human_validated": all(r.review == "accept" for r in train_records),
        "validation_human_validated": all(r.review == "accept" for r in val_records),
        "filename_labeled_crops": sum(r.review == "pending" for r in selected),
    }
    metadata = {
        "run_id": run_id,
        "status": "running",
        "fingerprint": signature,
        "configuration": settings.model_dump(mode="json"),
        "versions": versions(),
        "classes": classes.model_dump(mode="json"),
        "device": settings.device,
        "amp_dtype": str(dtype),
        "initial_checkpoint_sha256": file_hash(initial_checkpoint)
        if initial_checkpoint is not None
        else resume.get("initial_checkpoint_sha256")
        if resume
        else None,
        "label_provenance": provenance,
        "resume_checkpoint": str(checkpoints.path("last.pt")),
        "best_checkpoint": str(checkpoints.path("best.pt")),
        "oom_events": resume.get("oom_events", []) if resume else [],
    }
    journal.write_json(
        "manifest.json",
        {
            "class_manifest_version": classes.version,
            "crops": [r.model_dump(mode="json") for r in selected],
            "video_truth": truth,
        },
    )
    checkpoints.write_json("config.json", settings.model_dump(mode="json"))
    profile = resume.get("preprocessing") if resume else None
    if not resume and initial_checkpoint is None and config.initialization == "pretrained":
        from ..classification.pretrained import create_pretrained_model

        pretrained = config.pretrained_manifest or (
            settings.checkpoint_root.parent
            / "models/pretrained"
            / config.model_name
            / "manifest.json"
        )
        model, profile = create_pretrained_model(
            config.model_name, len(classes.names), pretrained, config.image_size
        )
    else:
        model = create_model(config.model_name, classes)
    if resume:
        model.load_state_dict(resume["state_dict"], strict=True)
    elif initial_checkpoint is not None:
        data = torch.load(initial_checkpoint, map_location="cpu", weights_only=True)
        classes.check_checkpoint(data)
        if data["model_name"] != config.model_name or data["img_size"] != config.image_size:
            raise ModelError("Architecture ou taille du checkpoint initial incompatible")
        model.load_state_dict(data["state_dict"], strict=True)
        profile = data.get("preprocessing")
    model.to(settings.device)
    counts = Counter(r.label for r in train_records)
    raw_weights = [1 / counts[r.label] ** config.balance_exponent for r in train_records]
    weights = [min(w, min(raw_weights) * config.balance_max_ratio) for w in raw_weights]
    generator = torch.Generator().manual_seed(settings.seed)
    sampler = WeightedRandomSampler(
        weights, len(train_records), replacement=True, generator=generator
    )
    train_data = CropsDataset(
        train_records,
        storage,
        classes,
        build_transform(config.image_size, training=True, profile=profile),
        allow_filename_labels=config.allow_filename_labels,
    )
    val_data = CropsDataset(
        val_records,
        storage,
        classes,
        build_transform(config.image_size, profile=profile),
        allow_filename_labels=config.allow_filename_labels,
    )
    loss_fn = nn.CrossEntropyLoss(label_smoothing=config.label_smoothing)
    history = resume["history"] if resume else []
    best_score = resume["best_score"] if resume else -1.0
    best_state = resume["best_state_dict"] if resume else None
    batch = resume["batch_size"] if resume else config.batch_size
    accumulation = resume["accumulation_steps"] if resume else config.accumulation_steps
    first_phase = resume["phase_index"] if resume else 0
    schedule = [
        ("head", config.epochs_head, config.head_lr),
        ("finetune", config.epochs_finetune, config.finetune_lr),
    ]
    publish(journal, metadata, history, config.database_metrics)
    metadata["initialization"] = config.initialization
    metadata["preprocessing"] = profile
    metadata["missing_train_classes"] = sorted(missing)

    def snapshot() -> dict[str, Any]:
        return {
            "training_schema": "2",
            "preprocessing": profile,
            "run_id": run_id,
            "fingerprint": signature,
            "configuration": settings.model_dump(mode="json"),
            "initial_checkpoint_sha256": metadata["initial_checkpoint_sha256"],
            "state_dict": model.state_dict(),
            "best_state_dict": best_state,
            "classes": list(classes.names),
            "class_manifest_version": classes.version,
            "model_name": config.model_name,
            "img_size": config.image_size,
            "label_provenance": provenance,
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "scaler": scaler.state_dict(),
            "phase_index": phase_index,
            "epoch": epoch,
            "stale": stale,
            "best_score": best_score,
            "history": history,
            "rng": rng_state(generator, settings.device == "cuda"),
            "batch_size": batch,
            "accumulation_steps": accumulation,
            "oom_events": metadata["oom_events"],
            "versions": metadata["versions"],
        }

    try:
        for phase_index in range(first_phase, 2):
            phase, epochs, lr = schedule[phase_index]
            continuing = resume is not None and phase_index == first_phase
            if phase_index == 1 and not continuing and best_state is not None:
                model.load_state_dict(best_state)
            configure_trainable(model, phase, 0, config.unfreeze_every)
            head = list(model.get_classifier().parameters())
            head_ids = {id(parameter) for parameter in head}
            groups = [{"params": head, "lr": lr if phase == "head" else config.finetune_head_lr}]
            if phase == "finetune":
                groups.append(
                    {"params": [p for p in model.parameters() if id(p) not in head_ids], "lr": lr}
                )
            if config.initialization == "legacy":
                for parameter in model.parameters():
                    parameter.requires_grad = phase == "finetune"
                for parameter in head:
                    parameter.requires_grad = True
                groups = [{"params": [p for p in model.parameters() if p.requires_grad], "lr": lr}]
            optimizer = torch.optim.AdamW(
                groups,
                lr=lr,
                weight_decay=config.weight_decay,
            )
            scheduler = (
                torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
                if config.scheduler == "cosine"
                else torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
            )
            scaler = torch.amp.GradScaler("cuda", enabled=dtype == torch.float16)
            epoch, stale = (resume["epoch"], resume["stale"]) if continuing else (0, 0)
            if continuing:
                optimizer.load_state_dict(resume["optimizer"])
                scheduler.load_state_dict(resume["scheduler"])
                scaler.load_state_dict(resume["scaler"])
                restore_rng(resume["rng"], generator)

            save_checkpoint(checkpoints, "last.pt", snapshot())
            retries = 0
            while epoch < epochs and stale < config.patience:
                configure_trainable(model, phase, epoch, config.unfreeze_every)
                if config.initialization == "legacy" and phase == "finetune":
                    for parameter in model.parameters():
                        parameter.requires_grad = True
                if stop.is_set():
                    raise TrainingInterrupted("Entraînement interrompu ; last.pt conservé")
                loader_args = {
                    "batch_size": batch,
                    "num_workers": config.num_workers,
                    "worker_init_fn": seed_worker,
                }
                train_loader = DataLoader(train_data, sampler=sampler, **loader_args)
                val_loader = DataLoader(val_data, shuffle=False, **loader_args)
                try:
                    loss = train_epoch(
                        model,
                        train_loader,
                        optimizer,
                        scaler,
                        loss_fn,
                        settings.device,
                        dtype,
                        accumulation,
                        phase,
                        stop,
                    )
                    metrics = evaluate_loader(
                        model,
                        val_loader,
                        settings.device,
                        loss_fn,
                        classes,
                        val_records,
                        truth,
                        dtype,
                    )
                except torch.OutOfMemoryError as exc:
                    optimizer.zero_grad(set_to_none=True)
                    gc.collect()
                    if settings.device == "cuda":
                        torch.cuda.empty_cache()
                    if batch == 1 or retries >= config.oom_retries:
                        raise ModelError(
                            "Mémoire insuffisante ; last.pt conservé. "
                            "Réduire la taille d'image pour un nouveau run."
                        ) from exc
                    previous_batch = batch
                    batch = max(1, batch // 2)
                    accumulation = math.ceil(config.batch_size * config.accumulation_steps / batch)
                    retries += 1
                    boundary = torch.load(
                        checkpoints.path("last.pt"), map_location="cpu", weights_only=True
                    )
                    model.load_state_dict(boundary["state_dict"])
                    optimizer.state.clear()
                    optimizer.load_state_dict(boundary["optimizer"])
                    scheduler.load_state_dict(boundary["scheduler"])
                    scaler = torch.amp.GradScaler("cuda", enabled=dtype == torch.float16)
                    scaler.load_state_dict(boundary["scaler"])
                    restore_rng(boundary["rng"], generator)
                    metadata["oom_events"].append(
                        {
                            "phase": phase,
                            "epoch": epoch + 1,
                            "previous_batch": previous_batch,
                            "batch_size": batch,
                            "accumulation_steps": accumulation,
                        }
                    )
                    logger.warning(
                        "OOM : reprise de l'époque avec batch=%s, accumulation=%s",
                        batch,
                        accumulation,
                    )
                    continue
                epoch += 1
                scheduler.step()
                score = metrics["macro_f1"]
                history.append(
                    {
                        "event_key": f"{phase}:{epoch}",
                        "phase": phase,
                        "epoch": epoch,
                        "train_loss": loss,
                        "validation": metrics,
                        "batch_size": batch,
                        "accumulation_steps": accumulation,
                    }
                )
                if score > best_score + 1e-5:
                    best_score, stale, best_state = score, 0, cpu_state(model.state_dict())
                    save_checkpoint(
                        checkpoints,
                        "best.pt",
                        {
                            "state_dict": best_state,
                            "preprocessing": profile,
                            "training_config": config.model_dump(mode="json"),
                            "dataset_version": file_hash(settings.train_manifest)
                            if settings.train_manifest
                            else signature,
                            "classes": list(classes.names),
                            "class_manifest_version": classes.version,
                            "model_name": config.model_name,
                            "img_size": config.image_size,
                            "val_macro_f1": best_score,
                            "label_provenance": provenance,
                            "run_id": run_id,
                        },
                    )
                else:
                    stale += 1
                # Le checkpoint est la source de vérité ; l'historique SQL/JSON est rejouable.
                save_checkpoint(checkpoints, "last.pt", snapshot())
                metadata.update(best_macro_f1=best_score, phase=phase, epoch=epoch)
                publish(journal, metadata, history, config.database_metrics)
                logger.info(
                    "%s %s/%s : perte=%.4f macro-F1=%.4f", phase, epoch, epochs, loss, score
                )
        metadata["status"] = "completed"
        if settings.device == "cuda":
            metadata["gpu_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
            metadata["gpu_total_memory_bytes"] = torch.cuda.get_device_properties(0).total_memory
    except BaseException as exc:
        metadata["status"] = (
            "interrupted" if isinstance(exc, TrainingInterrupted | KeyboardInterrupt) else "error"
        )
        publish(journal, metadata, history, config.database_metrics)
        raise
    publish(journal, metadata, history, config.database_metrics)
    # Compatibilité historique : chaque run possède ses propres artefacts persistants.
    storage.write_json("training_history.json", history)
    return {
        "run_id": run_id,
        "checkpoint": str(checkpoints.path("best.pt")),
        "resume_checkpoint": str(checkpoints.path("last.pt")),
        "best_macro_f1": best_score,
        "history": history,
        "label_provenance": provenance,
        "initialized_from_local_checkpoint": initial_checkpoint is not None,
        "status": "completed",
    }
