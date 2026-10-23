"""CLI locale de soumission, indépendante du GPU."""

import argparse
import json
from uuid import UUID

from shared.documents import service
from shared.documents.schemas import ManualImport, Search, Watch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    watch = commands.add_parser("watch")
    watch.add_argument("--name", required=True)
    watch.add_argument("--interval", type=int, default=86400)
    watch.add_argument("--enabled", action="store_true")
    for command in (search, watch):
        command.add_argument("--species", action="append", default=[])
        command.add_argument("--habitat", action="append", default=[])
        command.add_argument("--territory", action="append", default=[])
        command.add_argument("--topic", action="append", default=[])
        command.add_argument("--sources", nargs="+", default=["openalex", "crossref", "europepmc"])
        command.add_argument("--limit", type=int, default=20)
        command.add_argument("--download-fulltext", action="store_true")
    run = commands.add_parser("run-watch")
    run.add_argument("id", type=UUID)
    status = commands.add_parser("status")
    status.add_argument("id", type=UUID)
    imported = commands.add_parser("import")
    imported.add_argument("path")
    imported.add_argument("--title")
    imported.add_argument("--doi")
    imported.add_argument("--license")
    imported.add_argument("--rights-confirmed", action="store_true")
    fetch = commands.add_parser("fetch")
    fetch.add_argument("id", type=UUID)
    args = parser.parse_args()
    try:
        if args.command in ("search", "watch"):
            query = Search(
                species=args.species,
                habitats=args.habitat,
                territories=args.territory,
                topics=args.topic,
                sources=args.sources,
                limit_per_source=args.limit,
                download_fulltext=args.download_fulltext,
            )
            if args.command == "watch":
                result = service.watch(
                    Watch(
                        name=args.name,
                        search=query,
                        interval_seconds=args.interval,
                        enabled=args.enabled,
                    ),
                    "local-cli",
                )
            else:
                result = service.submit("search", {"search": query.model_dump()}, "local-cli")
        elif args.command == "run-watch":
            result = service.run_watch(str(args.id), "local-cli")
        elif args.command == "status":
            result = service.task(str(args.id))
        elif args.command == "fetch":
            service.document(str(args.id))
            result = service.submit("fetch", {"document_id": str(args.id)}, "local-cli")
        else:
            body = ManualImport(
                path=args.path,
                title=args.title,
                doi=args.doi,
                license=args.license,
                rights_confirmed=args.rights_confirmed,
            )
            result = service.submit("import", body.model_dump(), "local-cli")
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
