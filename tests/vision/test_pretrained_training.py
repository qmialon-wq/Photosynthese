import json

import pytest
from biosentinelle_vision.classification.pretrained import create_pretrained_model, load_asset
from biosentinelle_vision.config import TrainingConfig
from biosentinelle_vision.datasets.inventory import file_hash
from biosentinelle_vision.errors import ModelError


def test_pretrained_is_the_default_and_missing_weights_never_download(tmp_path):
    assert TrainingConfig().initialization == "pretrained"
    with pytest.raises(ModelError, match="absents"):
        load_asset(tmp_path / "absent.json")


@pytest.mark.ml
def test_local_imagenet_weights_replace_head_without_network(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    timm = pytest.importorskip("timm")
    from biosentinelle_vision.classification.preprocessing import build_transform
    from biosentinelle_vision.training.engine import configure_trainable
    from PIL import Image
    from safetensors.torch import save_file

    torch.set_num_threads(2)
    # Poids synthétiques au format des poids généralistes, réservés au test.
    source = timm.create_model("tf_efficientnetv2_b0.in1k", pretrained=False)
    weights = tmp_path / "model.safetensors"
    save_file(source.state_dict(), str(weights))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "pretrained-1",
                "architecture": "tf_efficientnetv2_b0",
                "timm_model": "tf_efficientnetv2_b0.in1k",
                "weights_key": "model.safetensors",
                "sha256": file_hash(weights),
                "revision": "test-fixture",
                "pretrained_cfg": {
                    "mean": [0.485, 0.456, 0.406],
                    "std": [0.229, 0.224, 0.225],
                    "interpolation": "bicubic",
                },
            }
        ),
        encoding="utf-8",
    )
    import socket

    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("Network forbidden")
    )
    model, profile = create_pretrained_model("tf_efficientnetv2_b0", 10, manifest, 32)
    assert model.get_classifier().out_features == 10
    configure_trainable(model, "head", 0, 2)
    frozen = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    configure_trainable(model, "finetune", 0, 2)
    assert sum(p.numel() for p in model.parameters() if not p.requires_grad) < frozen
    configure_trainable(model, "finetune", 100, 2)
    assert all(p.requires_grad for p in model.parameters())
    tensor = build_transform(32, profile=profile)(Image.new("RGB", (48, 48)))
    assert model.eval()(tensor.unsqueeze(0)).shape == (1, 10)
    weights.write_bytes(b"corrupt")
    with pytest.raises(ModelError, match="corrompus"):
        load_asset(manifest)
