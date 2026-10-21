import importlib.util

import pytest


@pytest.mark.gpu
def test_cuda_computation() -> None:
    # Sélection explicite avec -m gpu ; l'absence de CUDA devient alors un échec.
    assert importlib.util.find_spec("torch") is not None, "PyTorch absent de cet environnement"
    from workers.vision.cuda_check import check_cuda

    assert check_cuda()["status"] == "ok"
