"""Opérations exécutées dans le consommateur vision existant."""

from typing import Any

from ..config import VisionSettings
from ..storage import LocalStorage

KINDS = {
    "embeddings_extract",
    "embeddings_train",
    "embeddings_cluster",
    "classifiers_compare",
    "model_promote",
}


def perform(
    kind: str,
    payload: dict[str, Any],
    settings: VisionSettings,
    *,
    task_id: str | None = None,
    actor: str = "local-cli",
) -> dict[str, Any]:
    results = LocalStorage(settings.output_root)
    if kind == "model_promote":
        from shared.promotion import promote
        from shared.review.database import transaction

        from ..datasets.inventory import file_hash

        with transaction() as connection:
            models = connection.execute(
                "SELECT checkpoint_key,sha256 FROM console_models WHERE active OR id=%s",
                (payload["candidate_id"],),
            ).fetchall()
        for model in models:
            if (
                file_hash(LocalStorage(settings.checkpoint_root).path(model["checkpoint_key"]))
                != model["sha256"]
            ):
                raise ValueError("Le checkpoint évalué a été modifié")
        return promote(
            payload["candidate_id"],
            payload["comparison_id"],
            actor,
            manual_reason=payload.get("manual_reason", ""),
        )
    if kind == "classifiers_compare":
        import hashlib

        from shared.review.database import jsonb, transaction

        from ..classes import load_classes
        from ..datasets.benchmark import canonical
        from ..evaluation.comparison import compare_classifiers
        from ..training.evaluation import load_video_truth
        from .contracts import ModelVersion

        if task_id is None:
            raise ValueError("Comparaison durable : identifiant de tâche requis")
        models = [
            ModelVersion.model_validate(
                {
                    **row,
                    "checkpoint": LocalStorage(settings.checkpoint_root).path(row["checkpoint"]),
                }
            )
            for row in payload["models"]
        ]
        classes = load_classes(settings.classes_manifest)
        truth = (
            load_video_truth(results.path(payload["video_truth_key"]), classes)
            if payload.get("video_truth_key")
            else {}
        )
        report = compare_classifiers(
            results.path(payload["manifest_key"]),
            results.path(payload.get("storage_key", "")),
            models,
            results.path(f"comparisons/{task_id}.json"),
            classes,
            split=payload.get("split", "val"),
            threshold=payload.get("threshold", 0.48),
            batch_size=payload.get("batch_size", 2),
            device=settings.device,
            lock=settings.gpu_lock_path,
            video_truth=truth,
            allow_weak_labels=payload.get("allow_weak_labels", False),
        )
        with transaction(write=True) as connection:
            connection.execute(
                """INSERT INTO classifier_comparisons(id,report,report_sha256,actor)
                VALUES(%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
                (task_id, jsonb(report), hashlib.sha256(canonical(report)).hexdigest(), actor),
            )
        return {"comparison_id": task_id, "report_key": f"comparisons/{task_id}.json"}
    if kind == "embeddings_cluster":
        from ..evaluation.clustering import cluster_embeddings

        return cluster_embeddings(
            results.path(payload["index_key"]),
            results.path(payload["output_key"]),
            clusters=payload.get("clusters", 10),
            method=payload.get("method", "kmeans"),
            seed=payload.get("seed", 42),
        )
    architecture = payload.get("architecture", "tf_efficientnetv2_b0")
    from .pretrained import PRETRAINED_MODELS

    if architecture not in PRETRAINED_MODELS:
        raise ValueError("Architecture généraliste inconnue")
    pretrained = (
        settings.checkpoint_root.parent / "models/pretrained" / architecture / "manifest.json"
    )
    if kind == "embeddings_extract":
        from .embeddings import extract_embeddings

        return extract_embeddings(
            results.path(payload["manifest_key"]),
            results.path(payload.get("storage_key", "")),
            results.path("embeddings"),
            pretrained,
            device=settings.device,
            image_size=payload.get("image_size", 224),
            batch_size=payload.get("batch_size", 2),
            allow_weak_labels=payload.get("allow_weak_labels", False),
            lock=settings.gpu_lock_path,
        )
    if kind == "embeddings_train":
        from ..training.embedding import train_embedding_classifier

        return train_embedding_classifier(
            results.path(payload["index_key"]),
            LocalStorage(settings.checkpoint_root).path(payload["output_key"]),
            pretrained,
            candidates=tuple(payload.get("candidates", ["logistic", "knn", "linear_svm"])),
            seed=payload.get("seed", 42),
            allow_weak_validation=payload.get("allow_weak_validation", False),
        )
    raise ValueError(f"Opération de classification inconnue : {kind}")
