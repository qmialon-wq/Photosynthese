"""Collecte par espèce et retrait atomique du corpus, sans validation humaine inventée."""

from typing import Any

from shared.documents import service
from shared.documents.schemas import Search
from shared.review.database import ReviewError


def collect(species: list[str], actor: str) -> dict[str, Any]:
    with service.transaction(write=True) as connection:
        rows = connection.execute(
            "SELECT * FROM document_species_catalog WHERE %s OR name=ANY(%s) ORDER BY class_index",
            (not species, species),
        ).fetchall()
        jobs = []
        for row in rows:
            active = connection.execute(
                """SELECT id,status FROM document_tasks
              WHERE kind='search' AND status IN ('queued','running')
              AND request->>'collection_species'=%s ORDER BY created_at LIMIT 1""",
                (row["name"],),
            ).fetchone()
            if active:
                jobs.append(
                    {"id": str(active["id"]), "status": active["status"], "species": row["name"]}
                )
                continue
            query = Search(
                species=[row["scientific_name"]],
                focus="human_activities",
                sources=["openalex", "europepmc"],
                limit_per_source=5,
                download_fulltext=True,
            )
            job = service.submit(
                "search",
                {"search": query.model_dump(), "collection_species": row["name"]},
                actor,
                connection=connection,
            )
            jobs.append({**job, "species": row["name"]})
        return {"tasks": jobs}


def remove(species: str, documents: list[str], actor: str) -> dict[str, Any]:
    identifiers = list(dict.fromkeys(str(service.document(i)["id"]) for i in documents))
    with service.transaction(write=True) as connection:
        rows = connection.execute(
            """SELECT document_id FROM document_species
          WHERE species=%s AND document_id=ANY(%s::uuid[])""",
            (species, identifiers),
        ).fetchall()
        if len(rows) != len(identifiers):
            raise ReviewError("Tous les documents doivent appartenir à l'espèce choisie", 422)
        connection.execute(
            """UPDATE document_species SET excluded=true,enabled=false,
          origin='human',actor=%s,updated_at=now()
          WHERE species=%s AND document_id=ANY(%s::uuid[])""",
            (actor, species, identifiers),
        )
        for identifier in identifiers:
            connection.execute(
                """INSERT INTO document_selection_history
              (document_id,species,enabled,actor) VALUES(%s,%s,false,%s)""",
                (identifier, species, actor),
            )
            service.event(
                None,
                "selection",
                "Document retiré du corpus",
                document=identifier,
                data={"actor": actor, "species": species},
                connection=connection,
            )
    return {"removed": identifiers, "species": species}
