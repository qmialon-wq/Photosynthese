"""Téléchargement explicite de poids généralistes, puis chargement local vérifié."""

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..datasets.inventory import file_hash
from ..errors import ModelError
from ..storage import LocalStorage

PRETRAINED_MODELS = {
    "tf_efficientnetv2_b0": "tf_efficientnetv2_b0.in1k",
    "efficientnetv2_s": "tf_efficientnetv2_s.in21k_ft_in1k",
    "convnext_tiny": "convnext_tiny.fb_in1k",
    "resnet50": "resnet50.a1_in1k",
}


def load_asset(manifest: Path) -> tuple[dict[str, Any], Path]:
    if not manifest.is_file():
        raise ModelError(
            f"Poids généralistes absents : {manifest}. Exécuter pretrained-fetch explicitement."
        )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    weights = LocalStorage(manifest.parent).path(data["weights_key"])
    if not weights.is_file() or file_hash(weights) != data["sha256"]:
        raise ModelError("Poids généralistes absents ou corrompus")
    if (
        data.get("schema_version") != "pretrained-1"
        or data["timm_model"] not in PRETRAINED_MODELS.values()
    ):
        raise ModelError("Manifeste de poids généralistes incompatible")
    return data, weights


def fetch_pretrained(architecture: str, root: Path, revision: str | None = None) -> dict[str, Any]:
    if architecture not in PRETRAINED_MODELS:
        raise ModelError("Architecture préentraînée non prise en charge")
    destination = LocalStorage(root / architecture)
    manifest = destination.path("manifest.json")
    if manifest.exists() and revision is None:
        data, _ = load_asset(manifest)
        return {**data, "manifest": str(manifest), "cached": True}
    import timm
    from huggingface_hub import HfApi, hf_hub_download

    model_name = PRETRAINED_MODELS[architecture]
    config = timm.get_pretrained_cfg(model_name)
    if config is None or not config.hf_hub_id:
        raise ModelError("Configuration timm préentraînée absente")
    info = HfApi().model_info(config.hf_hub_id, revision=revision, files_metadata=True)
    entry = next((f for f in info.siblings if f.rfilename == "model.safetensors"), None)
    lfs = entry.lfs if entry else None
    checksum = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
    if not checksum or not info.sha:
        raise ModelError("Poids safetensors sans empreinte officielle ; téléchargement refusé")
    downloaded = Path(
        hf_hub_download(
            config.hf_hub_id,
            "model.safetensors",
            revision=info.sha,
            cache_dir=str(root / "cache/huggingface"),
        )
    )
    if file_hash(downloaded) != checksum:
        raise ModelError("Empreinte officielle des poids incompatible")
    key = f"{info.sha}/model.safetensors"
    target = destination.path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".downloading")
    shutil.copyfile(downloaded, temporary)
    if file_hash(temporary) != checksum:
        temporary.unlink(missing_ok=True)
        raise ModelError("Copie des poids corrompue")
    os.replace(temporary, target)
    data = {
        "schema_version": "pretrained-1",
        "architecture": architecture,
        "timm_model": model_name,
        "repository": config.hf_hub_id,
        "revision": info.sha,
        "sha256": checksum,
        "weights_key": key,
        "pretrained_cfg": config.to_dict(),
    }
    destination.write_json("manifest.json", data)
    return {**data, "manifest": str(manifest), "cached": False}


def create_pretrained_model(
    architecture: str, classes: int, manifest: Path, image_size: int
) -> tuple[Any, dict[str, Any]]:
    import timm

    data, weights = load_asset(manifest)
    if data["architecture"] != architecture:
        raise ModelError("Poids généralistes d'une autre architecture")
    model = timm.create_model(
        data["timm_model"],
        pretrained=True,
        num_classes=classes,
        pretrained_cfg_overlay={"file": str(weights), "hf_hub_id": None, "url": None},
    )
    profile = {
        "version": "timm-local-imagenet-v1",
        "image_size": image_size,
        "mean": data["pretrained_cfg"]["mean"],
        "std": data["pretrained_cfg"]["std"],
        "interpolation": data["pretrained_cfg"].get("interpolation", "bicubic"),
        "pretrained_sha256": data["sha256"],
        "pretrained_revision": data["revision"],
    }
    return model, profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("architecture", choices=PRETRAINED_MODELS)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    print(json.dumps(fetch_pretrained(args.architecture, args.root, args.revision)))


if __name__ == "__main__":
    main()
