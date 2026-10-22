"""Extracteur généraliste gelé et cache persistant indexé par contenu."""

import hashlib
import json
from collections.abc import Callable, Sequence
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from ..classes import ClassManifest
from ..datasets.benchmark import canonical
from ..datasets.inventory import file_hash
from ..errors import ManifestError, ModelError
from ..schemas import CropsManifest
from ..storage import LocalStorage
from ..storage.gpu import exclusive_gpu
from ..training.dataset import select_samples
from .preprocessing import build_transform
from .pretrained import create_pretrained_model, load_asset


class FeatureExtractor(Protocol):
    identity: dict[str, Any]

    def extract(self, images: Sequence[Image.Image]) -> Any: ...


class TimmExtractor:
    def __init__(self, manifest: Path, *, image_size: int = 224, device: str = "cpu") -> None:
        data, _ = load_asset(manifest)
        self.model, profile = create_pretrained_model(data["architecture"], 0, manifest, image_size)
        self.model.to(device).eval()
        self.transform = build_transform(image_size, profile=profile)
        self.device = device
        self.identity = {
            "architecture": data["architecture"],
            "weights_sha256": data["sha256"],
            "revision": data["revision"],
            "profile": profile,
        }

    def extract(self, images: Sequence[Image.Image]) -> Any:
        import numpy as np
        import torch

        if not images:
            return np.empty((0, self.model.num_features), dtype=np.float32)
        with torch.inference_mode():
            batch = torch.stack([self.transform(image.convert("RGB")) for image in images]).to(
                self.device
            )
            output = self.model(batch).float().cpu().numpy()
        if output.ndim != 2 or not np.isfinite(output).all():
            raise ModelError("Embeddings invalides")
        return output


def extract_cached(
    source: CropsManifest,
    storage: LocalStorage,
    cache: LocalStorage,
    extractor: FeatureExtractor,
    classes: ClassManifest,
    *,
    batch_size: int = 2,
    allow_weak_labels: bool = False,
    check_cancelled: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    import numpy as np

    if batch_size < 1 or source.class_manifest_version != classes.version:
        raise ManifestError("Configuration d'extraction incompatible")
    records = select_samples(source.crops, classes, allow_filename_labels=allow_weak_labels)
    if not records:
        raise ManifestError("Aucun recadrage admissible pour les embeddings")
    identity_hash = hashlib.sha256(canonical(extractor.identity)).hexdigest()
    rows, missing, hits = [], [], 0
    for record in records:
        check_cancelled()
        digest = file_hash(storage.path(record.image_key))
        key = hashlib.sha256(canonical({"image": digest, "extractor": identity_hash})).hexdigest()
        cache_key = f"vectors/{key}.npy"
        row = {
            "crop_id": record.crop_id,
            "image_key": record.image_key,
            "image_sha256": digest,
            "video_id": record.frame.video_id,
            "group_id": record.frame.group_id,
            "split": record.frame.split,
            "label": record.label,
            "human_validated": record.review == "accept",
            "cache_key": cache_key,
        }
        rows.append(row)
        if cache.path(cache_key).exists():
            vector = np.load(cache.path(cache_key), allow_pickle=False)
            if vector.ndim != 1 or not np.isfinite(vector).all():
                raise ManifestError(f"Cache d'embeddings corrompu : {cache_key}")
            hits += 1
        else:
            missing.append(row)
    index = 0
    current_batch = batch_size
    while index < len(missing):
        check_cancelled()
        batch = missing[index : index + current_batch]
        images = []
        for row in batch:
            with Image.open(storage.path(row["image_key"])) as image:
                images.append(image.convert("RGB"))
        try:
            vectors = extractor.extract(images)
        except Exception as exc:
            # Pas d'import PyTorch sur le chemin CPU/cache pur.
            if (
                type(exc).__name__ not in ("OutOfMemoryError", "CudaOutOfMemoryError")
                or current_batch == 1
            ):
                raise
            current_batch = max(1, current_batch // 2)
            import torch

            torch.cuda.empty_cache()
            continue
        if len(vectors) != len(batch):
            raise ModelError("Nombre d'embeddings incompatible")
        for row, vector in zip(batch, vectors, strict=True):
            vector = np.asarray(vector, dtype=np.float32)
            if vector.ndim != 1 or not np.isfinite(vector).all():
                raise ModelError("Vecteur de caractéristiques invalide")
            buffer = BytesIO()
            np.save(buffer, vector, allow_pickle=False)
            cache.write_bytes(row["cache_key"], buffer.getvalue())
        index += len(batch)
    manifest = {
        "schema_version": "embeddings-1",
        "classes": classes.model_dump(mode="json"),
        "extractor": extractor.identity,
        "samples": rows,
    }
    version = hashlib.sha256(canonical(manifest)).hexdigest()
    cache.write_json(f"datasets/{version}.json", manifest)
    return {
        "version": version,
        "index": str(cache.path(f"datasets/{version}.json")),
        "samples": len(rows),
        "cache_hits": hits,
        "extracted": len(missing),
    }


def extract_embeddings(
    manifest: Path,
    storage_root: Path,
    output: Path,
    pretrained: Path,
    *,
    device: str = "cpu",
    image_size: int = 224,
    batch_size: int = 2,
    allow_weak_labels: bool = False,
    lock: Path,
    check_cancelled: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    from ..classes import load_classes

    source = CropsManifest.model_validate_json(manifest.read_text(encoding="utf-8"))
    with exclusive_gpu(device, lock):
        extractor = TimmExtractor(pretrained, image_size=image_size, device=device)
        try:
            result = extract_cached(
                source,
                LocalStorage(storage_root),
                LocalStorage(output),
                extractor,
                load_classes(),
                batch_size=batch_size,
                allow_weak_labels=allow_weak_labels,
                check_cancelled=check_cancelled,
            )
            result["pretrained_manifest"] = str(pretrained)
            return result
        finally:
            del extractor
            if device == "cuda":
                import torch

                torch.cuda.empty_cache()


def read_embeddings(index: Path) -> tuple[dict[str, Any], Any]:
    import numpy as np

    data = json.loads(index.read_text(encoding="utf-8"))
    if data.get("schema_version") != "embeddings-1" or not data.get("samples"):
        raise ManifestError("Index d'embeddings incompatible ou vide")
    cache = LocalStorage(index.parent.parent)
    matrix = np.stack(
        [np.load(cache.path(row["cache_key"]), allow_pickle=False) for row in data["samples"]]
    )
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ManifestError("Embeddings non finis ou dimensions incompatibles")
    return data, matrix
