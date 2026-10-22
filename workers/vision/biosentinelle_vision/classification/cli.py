"""CLI asynchrone ; aucun calcul long dans le client de soumission."""

import argparse
import json
from uuid import uuid4

from shared.classification_jobs import Clustering, DatasetPreparation, EmbeddingTraining, Extract


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
    for command in (extract, train):
        command.add_argument("--architecture", default="tf_efficientnetv2_b0")
    args = vars(parser.parse_args())
    kind = {
        "extract-embeddings": "embeddings_extract",
        "train-embeddings": "embeddings_train",
        "cluster-embeddings": "embeddings_cluster",
        "prepare-dataset": "classification_dataset",
    }[args.pop("kind")]
    if kind == "classification_dataset":
        args["exclude_blurry"] = not args.pop("keep_blurry")
        args = DatasetPreparation.model_validate(args).model_dump()
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
