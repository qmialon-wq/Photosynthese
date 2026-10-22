import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from .classes import load_classes
from .config import VisionSettings
from .datasets.frames import extract_frames
from .datasets.inventory import inventory
from .datasets.split import split_videos
from .detection.batch import detect_frames
from .errors import VisionError
from .evaluation.metrics import evaluate_predictions
from .schemas import FramesManifest, Inventory, PredictionsManifest
from .storage import LocalStorage
from .storage.gpu import exclusive_gpu


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="biosentinelle-vision")
    root.add_argument("--classes-manifest", type=Path)
    commands = root.add_subparsers(dest="command", required=True)
    inv = commands.add_parser("inventory", help="Inventorier et séparer les vidéos locales")
    inv.add_argument("directory", type=Path)
    inv.add_argument("--output", type=Path, required=True)
    inv.add_argument("--no-probe", action="store_true", help="Ne pas vérifier le décodage")
    extraction = commands.add_parser("extract-frames", help="Extraire des JPEG et leur manifeste")
    extraction.add_argument("--inventory", type=Path, required=True)
    extraction.add_argument("--output-dir", type=Path)
    detect = commands.add_parser("detect", help="Détecter avec des poids MegaDetector locaux")
    detect.add_argument("--frames", type=Path, required=True)
    detect.add_argument("--storage-root", type=Path)
    detect.add_argument("--weights", type=Path)
    evaluate = commands.add_parser("evaluate", help="Évaluer des probabilités et labels validés")
    evaluate.add_argument("--predictions", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    training = commands.add_parser("train", help="Entraîner sur les recadrages validés")
    training.add_argument("--manifest", type=Path)
    training.add_argument("--storage-root", type=Path)
    training.add_argument("--initial-checkpoint", type=Path)
    training.add_argument("--check-only", action="store_true")
    for command in ("analyze", "watch"):
        analysis = commands.add_parser(
            command,
            help="Analyser le dossier inbox"
            if command == "analyze"
            else "Surveiller les dépôts de vidéos dans inbox",
        )
        analysis.add_argument("--inbox", type=Path)
        analysis.add_argument("--video", help="Chemin relatif d'une vidéo dans inbox")
        analysis.add_argument("--force", action="store_true", default=None)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = VisionSettings()
        classes = load_classes(args.classes_manifest or settings.classes_manifest)
        if args.command == "train":
            from .commands import train_from_manifest, training_samples

            updates = {
                name: value
                for name, value in {
                    "train_manifest": args.manifest,
                    "output_root": args.storage_root,
                    "initial_checkpoint": args.initial_checkpoint,
                }.items()
                if value is not None
            }
            settings = VisionSettings.model_validate({**settings.model_dump(), **updates})
            if args.check_only:
                samples = training_samples(settings, classes)
                print(json.dumps({"validated_crops": len(samples), "status": "ready"}))
            else:
                result = train_from_manifest(settings, classes)
                print(
                    json.dumps(
                        {
                            "checkpoint": result["checkpoint"],
                            "best_macro_f1": result["best_macro_f1"],
                        }
                    )
                )
            return 0
        if args.command in ("analyze", "watch"):
            from .commands import input_videos, run_analyses, watch_inbox

            updates = {
                name: value
                for name, value in {
                    "inbox_root": args.inbox,
                    "analysis_video": args.video,
                    "analysis_force": args.force,
                }.items()
                if value is not None
            }
            settings = VisionSettings.model_validate({**settings.model_dump(), **updates})
            if args.command == "watch":
                watch_inbox(settings, classes)
                return 0
            results = run_analyses(input_videos(settings), settings, classes)
            errors = sum(row["status"] == "error" for row in results)
            print(
                json.dumps(
                    {
                        "videos": len(results),
                        "errors": errors,
                        "skipped": sum(row.get("skipped", False) for row in results),
                    }
                )
            )
            return 2 if errors else 0
        if args.command == "inventory":
            result = split_videos(
                inventory(args.directory, classes, probe=not args.no_probe),
                settings.split,
                settings.seed,
            )
            LocalStorage(args.output.parent).write_json(
                args.output.name, result.model_dump(mode="json")
            )
            print(
                json.dumps(
                    {
                        "videos": len(result.videos),
                        "errors": sum(v.error is not None for v in result.videos),
                    }
                )
            )
            return 2 if any(v.error for v in result.videos) or not result.videos else 0
        if args.command == "extract-frames":
            source = Inventory.model_validate_json(args.inventory.read_text(encoding="utf-8"))
            if source.class_manifest_version != classes.version:
                raise VisionError("Inventaire créé avec un autre manifeste de classes")
            result = extract_frames(
                source, LocalStorage(args.output_dir or settings.output_root), settings.frames
            )
            print(json.dumps({"frames": len(result.frames), "errors": len(result.issues)}))
            return 2 if result.issues or not result.frames else 0
        if args.command == "detect":
            from .detection.megadetector import MegaDetector

            source = FramesManifest.model_validate_json(args.frames.read_text(encoding="utf-8"))
            if source.class_manifest_version != classes.version or not source.frames:
                raise VisionError("Manifeste d'images vide ou incompatible")
            weights = args.weights or settings.detector_weights
            if weights is None:
                raise VisionError("Fournir --weights avec un fichier local .pt")
            with exclusive_gpu(settings.device, settings.gpu_lock_path):
                detector = MegaDetector(weights, settings)
                result = detect_frames(
                    source, detector, LocalStorage(args.storage_root or args.frames.parent)
                )
            errors = sum(item.error is not None for item in result.frames)
            print(json.dumps({"frames": len(result.frames), "errors": errors}))
            return 2 if errors else 0
        source = PredictionsManifest.model_validate_json(
            args.predictions.read_text(encoding="utf-8")
        )
        report = evaluate_predictions(source, classes)
        LocalStorage(args.output.parent).write_json(args.output.name, report)
        print(json.dumps({"evaluated_crops": report["crops"]["count"]}))
        return 0
    except (VisionError, ValidationError, OSError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Arrêt demandé.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
