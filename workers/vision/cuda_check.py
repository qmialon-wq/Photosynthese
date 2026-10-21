"""Diagnostic explicite : allocation CUDA et petit calcul, sans modèle."""

import json


def check_cuda() -> dict[str, str]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA indisponible : vérifier le pilote et la réservation NVIDIA")
    with torch.inference_mode():
        tensor = torch.tensor([2.0, 3.0], device="cuda")
        result = float((tensor * tensor).sum().item())
        torch.cuda.synchronize()
    if result != 13.0:
        raise RuntimeError("Le calcul CUDA a échoué")
    details = {
        "torch": torch.__version__,
        "cuda": str(torch.version.cuda),
        "device": torch.cuda.get_device_name(0),
        "status": "ok",
    }
    print(json.dumps(details), flush=True)
    return details


if __name__ == "__main__":
    check_cuda()
