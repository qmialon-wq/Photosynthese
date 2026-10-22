"""CLI asynchrone ; aucun calcul long dans le client de soumission."""

import argparse
import json
from uuid import UUID, uuid4

from shared.classification_jobs import (
    Clustering,
    Comparison,
    DatasetPreparation,
    EmbeddingTraining,
    Extract,
    Promotion,
    Rollback,
    freeze_comparison,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="kind", required=True)
    extract = commands.add_parser("extract-embeddings")
    extract.add_argument("--manifest-key", required=True)
    extract.add_argument("--storage-key", default="")
    extract.add_argument("--image-size", type=int, default=224)
    extract.add_argument("--batch-size", type=int, default=2)
    extract.add_argument("--allow-weak-labels", action="store_true")
    train = commands.add_parser("train-embeddings")
    train.add_argument("--index-key", required=True)
    train.add_argument("--output-key", required=True)
    train.add_argument("--candidates", nargs="+", default=["logistic", "knn", "linear_svm"])
    train.add_argument("--allow-weak-validation", action="store_true")
    cluster = commands.add_parser("cluster-embeddings")
    cluster.add_argument("--index-key", required=True)
    cluster.add_argument("--output-key", required=True)
    cluster.add_argument("--clusters", type=int, default=10)
    cluster.add_argument("--method", choices=("kmeans", "hdbscan"), default="kmeans")
    prepare = commands.add_parser("prepare-dataset")
    prepare.add_argument("--allow-weak-labels", action="store_true")
    prepare.add_argument("--keep-blurry", action="store_true")
    compare = commands.add_parser("compare-classifiers")
    compare.add_argument("--manifest-key", required=True)
    compare.add_argument("--storage-key", default="")
    compare.add_argument("--model-ids", nargs="+", required=True)
    compare.add_argument("--split", choices=("val", "test"), default="val")
    compare.add_argument("--confirm-final-test", action="store_true")
    compare.add_argument("--allow-weak-labels", action="store_true")
    compare.add_argument("--video-truth-key")
    compare.add_argument("--threshold", type=float, default=0.48)
    compare.add_argument("--batch-size", type=int, default=2)
    promote = commands.add_parser("promote-model")
    promote.add_argument("--candidate-id", type=UUID, required=True)
    promote.add_argument("--comparison-id", type=UUID, required=True)
    promote.add_argument("--manual-reason", default="")
    rollback = commands.add_parser("rollback-model")
    rollback.add_argument("--model-id", type=UUID, required=True)
    rollback.add_argument("--reason", required=True)
    for command in (extract, train):
        command.add_argument("--architecture", default="tf_efficientnetv2_b0")
    args = vars(parser.parse_args())
    kind = {
        "extract-embeddings": "embeddings_extract",
        "train-embeddings": "embeddings_train",
        "cluster-embeddings": "embeddings_cluster",
        "prepare-dataset": "classification_dataset",
        "compare-classifiers": "classifiers_compare",
        "promote-model": "model_promote",
        "rollback-model": "model_rollback",
    }[args.pop("kind")]
    if kind == "classification_dataset":
        args["exclude_blurry"] = not args.pop("keep_blurry")
        args = DatasetPreparation.model_validate(args).model_dump()
    elif kind == "classifiers_compare":
        args = freeze_comparison(Comparison.model_validate(args))
    elif kind == "model_promote":
        candidate = str(args.pop("candidate_id"))
        args = {"candidate_id": candidate, **Promotion.model_validate(args).model_dump(mode="json")}
    elif kind == "model_rollback":
        model = str(args.pop("model_id"))
        args = {"model_id": model, **Rollback.model_validate(args).model_dump(mode="json")}
    elif kind == "embeddings_extract":
        args = Extract.model_validate(args).model_dump()
    elif kind == "embeddings_train":
        output = args.pop("output_key")
        # Même confinement que les chemins API, vérifié à nouveau par LocalStorage.
        Extract.relative(output)
        args = {**EmbeddingTraining.model_validate(args).model_dump(), "output_key": output}
    elif kind == "embeddings_cluster":
        output = args.pop("output_key") or f"exploration/{uuid4()}.json"
        Extract.relative(output)
        args = {**Clustering.model_validate(args).model_dump(), "output_key": output}
    from shared.console import submit

    print(json.dumps(submit(kind, args, "local-cli")))


if __name__ == "__main__":
    main()
