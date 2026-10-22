import logging
import random
from collections import Counter
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any

from ..classes import ClassManifest
from ..classification.model import create_model
from ..classification.preprocessing import build_transform
from ..config import VisionSettings
from ..errors import ManifestError, ModelError
from ..evaluation.metrics import classification_metrics
from ..schemas import CropRecord
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from .dataset import CropsDataset, select_samples


def evaluate_loader(
    model: Any, loader: Any, device: str, loss_fn: Any, classes: ClassManifest
) -> dict[str, Any]:
    import torch

    truth, predicted, total_loss, count = [], [], 0.0, 0
    model.eval()
    with torch.inference_mode():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            total_loss += float(loss_fn(logits, labels).item()) * len(labels)
            count += len(labels)
            truth.extend(classes.names[i] for i in labels.cpu().tolist())
            predicted.extend(classes.names[i] for i in logits.argmax(1).cpu().tolist())
    if not count:
        raise ManifestError("Ensemble d'évaluation vide")
    return {**classification_metrics(truth, predicted, classes), "loss": total_loss / count}


def train(
    records: Sequence[CropRecord],
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
    *,
    initial_checkpoint: Path | None = None,
) -> dict[str, Any]:
    with exclusive_gpu(settings.device, settings.gpu_lock_path):
        return _train(records, storage, classes, settings, initial_checkpoint)


def _train(
    records: Sequence[CropRecord],
    storage: LocalStorage,
    classes: ClassManifest,
    settings: VisionSettings,
    initial_checkpoint: Path | None,
) -> dict[str, Any]:
    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, WeightedRandomSampler

    selected = select_samples(records, classes, settings.crops.max_per_video)
    train_records = [r for r in selected if r.frame.split == "train"]
    val_records = [r for r in selected if r.frame.split == "val"]
    missing = set(classes.names) - {r.label for r in train_records}
    if missing or not val_records:
        raise ManifestError(f"Validation vide ou classes sans train validé : {sorted(missing)}")
    if settings.device == "cuda" and not torch.cuda.is_available():
        raise ModelError("CUDA demandé mais indisponible")
    random.seed(settings.seed)
    np.random.seed(settings.seed)
    torch.manual_seed(settings.seed)
    config = settings.training
    model = create_model(config.model_name, classes)
    if initial_checkpoint is not None:
        data = torch.load(initial_checkpoint, map_location="cpu", weights_only=True)
        classes.check_checkpoint(data)
        if data["model_name"] != config.model_name or data["img_size"] != config.image_size:
            raise ModelError("Modèle ou taille d'image du checkpoint initial incompatible")
        model.load_state_dict(data["state_dict"], strict=True)
    model.to(settings.device)
    counts = Counter(r.label for r in train_records)
    sampler = WeightedRandomSampler(
        [1 / counts[r.label] ** 0.5 for r in train_records], len(train_records), replacement=True
    )
    train_loader = DataLoader(
        CropsDataset(
            train_records, storage, classes, build_transform(config.image_size, training=True)
        ),
        batch_size=config.batch_size,
        sampler=sampler,
        num_workers=config.num_workers,
    )
    val_loader = DataLoader(
        CropsDataset(val_records, storage, classes, build_transform(config.image_size)),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
    )
    loss_fn = nn.CrossEntropyLoss(label_smoothing=config.label_smoothing)
    checkpoints = LocalStorage(settings.checkpoint_root)
    checkpoint_key = "classifier_v3_best.pt"
    best_score, history = -1.0, []
    for phase, epochs, lr in (
        ("head", config.epochs_head, config.head_lr),
        ("finetune", config.epochs_finetune, config.finetune_lr),
    ):
        if phase == "finetune":
            best = torch.load(
                checkpoints.path(checkpoint_key), map_location="cpu", weights_only=True
            )
            model.load_state_dict(best["state_dict"])
        for parameter in model.parameters():
            parameter.requires_grad = phase == "finetune"
        for parameter in model.get_classifier().parameters():
            parameter.requires_grad = True
        optimizer = torch.optim.AdamW(
            (p for p in model.parameters() if p.requires_grad),
            lr=lr,
            weight_decay=config.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        stale = 0
        for epoch in range(1, epochs + 1):
            model.train() if phase == "finetune" else model.eval()
            model.get_classifier().train()
            total_loss, count = 0.0, 0
            for images, labels in train_loader:
                images, labels = images.to(settings.device), labels.to(settings.device)
                optimizer.zero_grad(set_to_none=True)
                loss = loss_fn(model(images), labels)
                if not torch.isfinite(loss):
                    raise ModelError("Perte d'entraînement non finie")
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += float(loss.detach().item()) * len(labels)
                count += len(labels)
            scheduler.step()
            metrics = evaluate_loader(model, val_loader, settings.device, loss_fn, classes)
            score = metrics["macro_f1"]
            history.append(
                {
                    "phase": phase,
                    "epoch": epoch,
                    "train_loss": total_loss / count,
                    "validation": metrics,
                }
            )
            logging.getLogger(__name__).info(
                "%s %s/%s : perte=%.4f, macro-F1 validation=%.4f",
                phase,
                epoch,
                epochs,
                total_loss / count,
                score,
            )
            if score > best_score + 1e-5:
                best_score, stale = score, 0
                buffer = BytesIO()
                torch.save(
                    {
                        "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        "classes": list(classes.names),
                        "class_manifest_version": classes.version,
                        "model_name": config.model_name,
                        "img_size": config.image_size,
                        "val_macro_f1": best_score,
                    },
                    buffer,
                )
                checkpoints.write_bytes(checkpoint_key, buffer.getvalue())
            else:
                stale += 1
            storage.write_json("training_history.json", history)
            if stale >= config.patience:
                break
    return {
        "checkpoint": str(checkpoints.path(checkpoint_key)),
        "best_macro_f1": best_score,
        "history": history,
        "initialized_from_local_checkpoint": initial_checkpoint is not None,
    }
