import threading
from typing import Any

from ..errors import ModelError, TrainingInterrupted


def amp_dtype(device: str, mode: str) -> Any:
    import torch

    if device != "cuda" or mode == "off":
        if device != "cuda" and mode in ("float16", "bfloat16"):
            raise ModelError("AMP explicite réservé à CUDA ; utiliser auto ou off sur CPU")
        return None
    if mode == "bfloat16" and not torch.cuda.is_bf16_supported():
        raise ModelError("AMP bfloat16 non pris en charge par ce GPU")
    return (
        torch.bfloat16
        if mode == "bfloat16" or (mode == "auto" and torch.cuda.is_bf16_supported())
        else torch.float16
    )


def train_epoch(
    model: Any,
    loader: Any,
    optimizer: Any,
    scaler: Any,
    loss_fn: Any,
    device: str,
    dtype: Any,
    accumulation: int,
    phase: str,
    stop: threading.Event,
) -> float:
    import torch
    from torch import nn

    model.train(phase == "finetune")
    model.get_classifier().train()
    for module in model.modules():
        parameters = list(module.parameters())
        if module is not model and parameters and not any(p.requires_grad for p in parameters):
            module.eval()
    if loader.batch_size == 1:
        # Une micro-batch de 1 ne permet pas d'estimer des statistiques BatchNorm stables.
        for module in model.modules():
            if isinstance(module, nn.modules.batchnorm._BatchNorm):
                module.eval()
    optimizer.zero_grad(set_to_none=True)
    total, count, group_count = 0.0, 0, 0
    for index, (images, labels) in enumerate(loader):
        if stop.is_set():
            raise TrainingInterrupted("Arrêt demandé ; reprendre depuis last.pt")
        images, labels = images.to(device), labels.to(device)
        with torch.autocast(device, dtype=dtype, enabled=dtype is not None):
            loss = loss_fn(model(images), labels)
        if not torch.isfinite(loss):
            raise ModelError("Perte d'entraînement non finie")
        # Somme des pertes, puis division par le nombre réel d'images du groupe,
        # y compris la dernière accumulation incomplète.
        scaler.scale(loss * len(labels)).backward()
        group_count += len(labels)
        total += float(loss.detach().item()) * len(labels)
        count += len(labels)
        if (index + 1) % accumulation == 0 or index + 1 == len(loader):
            scaler.unscale_(optimizer)
            for parameter in model.parameters():
                if parameter.grad is not None:
                    parameter.grad.div_(group_count)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            group_count = 0
    return total / count
