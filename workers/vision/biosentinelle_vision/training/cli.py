import argparse
import json
import os
import signal
import threading
from pathlib import Path
from typing import Any

from ..classes import ClassManifest
from ..config import VisionSettings
from ..errors import ModelError

COMMANDS = {"train-classifier", "evaluate-classifier", "metrics-sync", "detector-train-check"}


def register(commands: Any) -> None:
    for name in ("train-classifier", "evaluate-classifier"):
        parser = commands.add_parser(name)
        parser.add_argument("--config", type=Path)
        parser.add_argument("--manifest", type=Path)
        parser.add_argument("--storage-root", type=Path)
        parser.add_argument("--video-truth", type=Path)
        if name == "train-classifier":
            parser.add_argument(
                "--resume", type=Path, default=os.getenv("BIOSENTINELLE_TRAIN_RESUME")
            )
            parser.add_argument("--initial-checkpoint", type=Path)
            parser.add_argument("--run-id")
            parser.add_argument("--model")
            parser.add_argument("--batch-size", type=int)
            parser.add_argument("--accumulation-steps", type=int)
            parser.add_argument("--epochs-head", type=int)
            parser.add_argument("--epochs-finetune", type=int)
            parser.add_argument("--image-size", type=int)
            parser.add_argument("--amp", choices=("auto", "off", "float16", "bfloat16"))
            parser.add_argument(
                "--local", action="store_true", help="Exécution CPU hors file, pour tests"
            )
            parser.add_argument("--no-database", action="store_true")
            parser.add_argument("--allow-filename-labels", action="store_true")
        else:
            parser.add_argument("--checkpoint", type=Path)
            parser.add_argument("--split", choices=("train", "val", "test"), default="test")
    sync = commands.add_parser("metrics-sync")
    sync.add_argument("directory", type=Path)
    detector = commands.add_parser("detector-train-check")
    detector.add_argument("--config", type=Path, required=True)


def dispatch(args: argparse.Namespace, settings: VisionSettings, classes: ClassManifest) -> int:
    from .commands import enqueue_training, evaluate_classifier, sync_metrics

    if args.command == "metrics-sync":
        sync_metrics(args.directory)
        print(json.dumps({"database_sync": "ok"}))
        return 0
    if args.command == "detector-train-check":
        from .detector import DetectorTrainingConfig, validate_detector_dataset

        config = DetectorTrainingConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
        print(json.dumps(validate_detector_dataset(config)))
        return 0
    data = settings.model_dump(mode="json")
    data["training"]["allow_filename_labels"] = False
    resuming = args.command == "train-classifier" and args.resume is not None
    if args.config is None and not resuming and os.getenv("BIOSENTINELLE_TRAIN_CONFIG"):
        args.config = Path(os.environ["BIOSENTINELLE_TRAIN_CONFIG"])
    if args.command == "train-classifier" and args.resume:
        data = json.loads((args.resume.parent / "config.json").read_text(encoding="utf-8"))
        data["initial_checkpoint"] = None
        data["training"]["resume_checkpoint"] = str(args.resume)
    if args.config:
        overrides = json.loads(args.config.read_text(encoding="utf-8"))
        data["training"].update(overrides.pop("training", {}))
        data.update(overrides)
    for name, value in (("train_manifest", args.manifest), ("output_root", args.storage_root)):
        if value is not None:
            data[name] = str(value)
    if args.video_truth:
        data["training"]["video_truth_manifest"] = str(args.video_truth)
    if args.command == "evaluate-classifier":
        if args.checkpoint:
            data["classifier_checkpoint"] = str(args.checkpoint)
        config = VisionSettings.model_validate(data)
        if config.device == "cuda":
            job = enqueue_training(config, "evaluate_classifier", args.split)
            print(json.dumps({**job, "status_url": f"/vision/analyses/{job['id']}"}))
            return 0
        report = evaluate_classifier(config, classes, args.split)
        print(json.dumps(report))
        return 0
    if not resuming:
        for field in (
            "batch_size",
            "accumulation_steps",
            "image_size",
            "epochs_head",
            "epochs_finetune",
        ):
            value = os.getenv(f"BIOSENTINELLE_VISION_TRAINING__{field.upper()}")
            if value is not None:
                data["training"][field] = int(value)
    for field, option in (
        ("model_name", "model"),
        ("run_id", "run_id"),
        ("batch_size", "batch_size"),
        ("accumulation_steps", "accumulation_steps"),
        ("image_size", "image_size"),
        ("epochs_head", "epochs_head"),
        ("epochs_finetune", "epochs_finetune"),
        ("amp", "amp"),
    ):
        value = getattr(args, option)
        if value is not None:
            data["training"][field] = value
    if args.initial_checkpoint:
        data["initial_checkpoint"] = str(args.initial_checkpoint)
    if args.allow_filename_labels:
        data["training"]["allow_filename_labels"] = True
    data["training"]["database_metrics"] = not args.local and not args.no_database
    config = VisionSettings.model_validate(data)
    if args.local:
        if config.device != "cpu":
            raise ModelError(
                "Les entraînements GPU doivent passer par Redis ; --local est réservé au CPU"
            )
        from ..commands import train_from_manifest

        stop = threading.Event()
        previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            for s in previous:
                signal.signal(s, lambda *_: stop.set())
            print(json.dumps(train_from_manifest(config, classes, stop)))
        finally:
            for s, handler in previous.items():
                signal.signal(s, handler)
    else:
        job = enqueue_training(config)
        print(json.dumps({**job, "status_url": f"/vision/analyses/{job['id']}"}))
    return 0
