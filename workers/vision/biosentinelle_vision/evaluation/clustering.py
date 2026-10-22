"""Exploration uniquement : aucune correspondance automatique cluster -> espèce."""

from pathlib import Path
from typing import Any

from ..classification.embeddings import read_embeddings
from ..errors import ManifestError
from ..storage import LocalStorage


def cluster_embeddings(
    index: Path, output: Path, *, clusters: int = 10, method: str = "kmeans", seed: int = 42
) -> dict[str, Any]:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import Normalizer

    data, raw = read_embeddings(index)
    rows = data["samples"]
    train = np.asarray([r["split"] == "train" for r in rows])
    visible = np.asarray([r["split"] != "test" for r in rows])
    if int(train.sum()) < 2 or clusters < 1:
        raise ManifestError("Au moins deux embeddings train et un cluster requis")
    normalized = Normalizer().fit_transform(raw)
    projection = PCA(n_components=min(2, int(train.sum()), raw.shape[1]), random_state=seed)
    projection.fit(normalized[train])
    coordinates = projection.transform(normalized)
    if coordinates.shape[1] == 1:
        coordinates = np.column_stack([coordinates, np.zeros(len(rows))])
    if method == "kmeans":
        model = KMeans(n_clusters=min(clusters, int(train.sum())), n_init=10, random_state=seed)
        model.fit(normalized[train])
        labels = model.predict(normalized).astype(object)
        distances = model.transform(normalized).min(axis=1)
    elif method == "hdbscan":
        from sklearn.cluster import HDBSCAN

        model = HDBSCAN(min_cluster_size=min(5, max(2, int(train.sum()) // 4)), copy=True)
        model.fit(normalized[train])
        labels = np.full(len(rows), None, dtype=object)
        labels[train] = model.labels_
        distances = np.full(len(rows), np.nan)
        distances[train] = 1 - model.probabilities_
    else:
        raise ManifestError("Méthode de clustering inconnue")
    train_distances = distances[train & np.isfinite(distances)]
    threshold = float(np.quantile(train_distances, 0.95)) if len(train_distances) else 0.0
    points = [
        {
            "crop_id": row["crop_id"],
            "image_key": row["image_key"],
            "video_id": row["video_id"],
            "split": row["split"],
            "annotated_species": row["label"],
            "human_validated": row["human_validated"],
            "x": float(coordinates[i, 0]),
            "y": float(coordinates[i, 1]),
            "cluster_id": int(labels[i]) if labels[i] is not None else None,
            "anomaly_score": float(distances[i]) if np.isfinite(distances[i]) else None,
            "review_recommended": bool(
                np.isfinite(distances[i]) and distances[i] > threshold or labels[i] == -1
            ),
        }
        for i, row in enumerate(rows)
        if visible[i]
    ]
    report = {
        "schema_version": "clustering-1",
        "method": method,
        "projection": "pca_train_only",
        "seed": seed,
        "points": points,
        "test_excluded": True,
        "review_crop_ids": [p["crop_id"] for p in points if p["review_recommended"]],
        "warning": "Groupes visuels, pas des espèces. Aucune annotation modifiée.",
        "anomaly_method": "centroid_distance"
        if method == "kmeans"
        else "one_minus_cluster_membership",
    }
    LocalStorage(output.parent).write_json(output.name, report)
    return {
        "report": str(output),
        "points": len(points),
        "review_candidates": len(report["review_crop_ids"]),
    }
