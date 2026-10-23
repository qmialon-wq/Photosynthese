"""Explicit model preparation and CPU ONNX embeddings; no downloads on import/load."""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from shared.documents.service import canonical
from shared.rag.config import RagSettings


class Encoder(Protocol):
    version: str
    manifest: dict[str, Any]

    def encode(self, text: str, *, query: bool = False) -> list[float]: ...


def manifest(settings: RagSettings) -> dict[str, Any]:
    path = settings.model_manifest or Path(__file__).parents[2] / "shared/rag/model.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    if (
        not re.fullmatch(r"[\w.-]+/[\w.-]+", result["name"])
        or not re.fullmatch(r"[a-f0-9]{40}", result["revision"])
        or result["pooling"] != "mean"
        or result["normalization"] != "l2"
        or not 8 <= result["max_tokens"] <= 512
        or not 1 <= result["dimension"] <= 4096
        or set(result["files"]) != {"onnx/model_quantized.onnx", "tokenizer.json"}
        or any(not re.fullmatch(r"[a-f0-9]{64}", s) for s in result["files"].values())
    ):
        raise ValueError("Manifeste ONNX incompatible ou non épinglé")
    return result


def version(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical({"encoder": "onnx-mean-v1", "model": data})).hexdigest()


def checked(path: Path, sha: str) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest() == sha


def prepare(settings: RagSettings, http: Any) -> dict[str, Any]:
    data = manifest(settings)
    identifier = version(data)
    root = settings.model_root / identifier
    for name, sha in data["files"].items():
        path = root / name
        if checked(path, sha):
            continue
        url = f"https://huggingface.co/{data['name']}/resolve/{data['revision']}/{name}"
        content, _, _ = http.get(url, cache=False, max_bytes=128 * 1024 * 1024)
        if hashlib.sha256(content).hexdigest() != sha:
            raise ValueError(f"Intégrité du modèle invalide : {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        temporary.write_bytes(content)
        temporary.replace(path)
    (root / "manifest.json").write_bytes(canonical(data))
    return {"version": identifier, "model": data["name"], "status": "prepared"}


class OnnxEncoder:
    def __init__(self, settings: RagSettings) -> None:
        self.manifest = manifest(settings)
        self.version = version(self.manifest)
        root = settings.model_root / self.version
        for name, sha in self.manifest["files"].items():
            if not checked(root / name, sha):
                raise ValueError("Embeddings absents ou corrompus : exécuter make rag-prepare")
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = settings.threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(root / "onnx/model_quantized.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

    def encode(self, text: str, *, query: bool = False) -> list[float]:
        import numpy as np

        prefix = self.manifest["query_prefix" if query else "passage_prefix"]
        tokens = self.tokenizer.encode(prefix + text, add_special_tokens=False).ids
        cls_id = self.tokenizer.token_to_id("<s>")
        sep_id = self.tokenizer.token_to_id("</s>")
        if cls_id is None or sep_id is None:
            raise ValueError("Tokenizer incompatible : modèle XLM-R requis")
        # Split rather than silently discarding the end of a long scientific fragment.
        step = self.manifest["max_tokens"] - 2
        vectors, weights = [], []
        for start in range(0, max(1, len(tokens)), step):
            ids = np.array([[cls_id, *tokens[start : start + step], sep_id]], dtype=np.int64)
            values = {"input_ids": ids, "attention_mask": np.ones_like(ids)}
            values["token_type_ids"] = np.zeros_like(ids)
            inputs = {i.name: values[i.name] for i in self.session.get_inputs()}
            output = self.session.run(None, inputs)[0]
            if output.ndim != 3 or output.shape[-1] != self.manifest["dimension"]:
                raise ValueError("Sortie ONNX incompatible avec mean pooling")
            vectors.append(output[0].mean(axis=0))
            weights.append(ids.shape[1])
        vector = np.average(vectors, axis=0, weights=weights)
        norm = np.linalg.norm(vector)
        if not np.isfinite(vector).all() or norm == 0:
            raise ValueError("Embedding invalide")
        return (vector / norm).tolist()


@lru_cache(maxsize=1)
def encoder(model_root: str, model_manifest: str | None, threads: int) -> OnnxEncoder:
    return OnnxEncoder(
        RagSettings(model_root=model_root, model_manifest=model_manifest, threads=threads)
    )


def load(settings: RagSettings) -> Encoder:
    return encoder(
        str(settings.model_root),
        str(settings.model_manifest) if settings.model_manifest else None,
        settings.threads,
    )
