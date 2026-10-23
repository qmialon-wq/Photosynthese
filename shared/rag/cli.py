"""Submit CPU RAG jobs and inspect results. Nothing runs during import."""

import argparse
import json
from pathlib import Path

from shared.documents import service as documents
from shared.rag import service
from shared.rag.schemas import Evaluation, Index, Report, Search


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    index = commands.add_parser("index")
    index.add_argument("--document", action="append", default=[])
    for kind in ("search", "report", "evaluate"):
        sub = commands.add_parser(kind)
        sub.add_argument("--file", type=Path, help="JSON request stored inside the container")
        if kind != "evaluate":
            sub.add_argument("--question")
            sub.add_argument("--species", action="append", default=[])
            sub.add_argument("--mode", choices=["hybrid", "lexical"], default="hybrid")
    status = commands.add_parser("status")
    status.add_argument("id")
    run = commands.add_parser("result")
    run.add_argument("id")
    args = parser.parse_args()
    if args.command == "status":
        result = documents.task(args.id)
    elif args.command == "result":
        result = service.run(args.id)
    else:
        if args.command == "prepare":
            body = {}
        elif args.command == "index":
            body = Index(document_ids=args.document).model_dump(mode="json")
        else:
            if args.file:
                payload = json.loads(args.file.read_text(encoding="utf-8"))
            elif args.command == "evaluate":
                parser.error("--file requis")
            else:
                payload = {
                    "question": args.question,
                    "filters": {"species": args.species},
                    "mode": args.mode,
                }
            schema = {"search": Search, "report": Report, "evaluate": Evaluation}[args.command]
            body = schema.model_validate(payload).model_dump(mode="json")
        result = service.submit(args.command, body, "local-cli")
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
