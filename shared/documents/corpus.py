"""Associations par espèce, sélection explicite et corpus effectivement disponible."""

from typing import Any

from shared.documents import service
from shared.review.database import ReviewError

# Même condition pour le catalogue, la liste et les décisions d'ajout.
READY = """d.status='indexed' AND d.relevance='accepted' AND d.quality='accepted'
    AND EXISTS(SELECT 1 FROM document_assets a JOIN document_chunks ch ON ch.asset_id=a.id
               WHERE a.document_id=d.id)"""


def catalog() -> list[dict[str, Any]]:
    with service.transaction() as connection:
        return connection.execute(f"""SELECT c.*,
          count(d.id) AS documents_count,
          count(d.id) FILTER(WHERE s.enabled AND {READY}) AS selected_count
          FROM document_species_catalog c
          LEFT JOIN document_species s ON s.species=c.name
          LEFT JOIN scientific_documents d ON d.id=s.document_id AND d.merged_into IS NULL
          GROUP BY c.name ORDER BY c.class_index""").fetchall()


def discover(document_id: str, terms: list[str], actor: str) -> None:
    document_id = str(service.document(document_id)["id"])
    with service.transaction(write=True) as connection:
        connection.execute(
            """INSERT INTO document_species(document_id,species,origin,actor)
          SELECT %s,name,'discovery',%s FROM document_species_catalog
          WHERE lower(name)=ANY(%s) OR lower(scientific_name)=ANY(%s)
          ON CONFLICT DO NOTHING""",
            (document_id, actor, [t.lower() for t in terms], [t.lower() for t in terms]),
        )


def links(document_id: str) -> list[dict[str, Any]]:
    with service.transaction() as connection:
        return connection.execute(
            f"""SELECT s.*, c.display_name,c.scientific_name,
          (s.enabled AND {READY}) AS available
          FROM document_species s JOIN document_species_catalog c ON c.name=s.species
          JOIN scientific_documents d ON d.id=s.document_id
          WHERE s.document_id=%s ORDER BY c.class_index""",
            (document_id,),
        ).fetchall()


def select(document_id: str, species: str, enabled: bool, actor: str) -> dict[str, Any]:
    document_id = str(service.document(document_id)["id"])
    with service.transaction(write=True) as connection:
        if not connection.execute(
            "SELECT 1 FROM document_species_catalog WHERE name=%s", (species,)
        ).fetchone():
            raise ReviewError("Espèce inconnue", 422)
        if enabled:
            ready = connection.execute(
                """SELECT 1 FROM scientific_documents d
              WHERE d.id=%s AND d.status='indexed' AND EXISTS(
              SELECT 1 FROM document_assets a JOIN document_chunks c ON c.asset_id=a.id
              WHERE a.document_id=d.id)""",
                (document_id,),
            ).fetchone()
            if not ready:
                raise ReviewError(
                    "Un texte intégral indexé et non rejeté est requis pour l'ajout", 409
                )
            # « Valider et ajouter » constitue la décision humaine, sans commentaire requis.
            connection.execute(
                """INSERT INTO document_reviews
              (document_id,relevance,quality,note,actor) VALUES(%s,'accepted','accepted',%s,%s)""",
                (document_id, f"Sélection documentaire pour {species}", actor),
            )
            connection.execute(
                """UPDATE scientific_documents SET relevance='accepted',
              quality='accepted',updated_at=now() WHERE id=%s""",
                (document_id,),
            )
        connection.execute(
            """INSERT INTO document_species(document_id,species,enabled,origin,actor)
          VALUES(%s,%s,%s,'human',%s) ON CONFLICT(document_id,species) DO UPDATE
          SET enabled=excluded.enabled,origin='human',actor=excluded.actor,updated_at=now()""",
            (document_id, species, enabled, actor),
        )
        connection.execute(
            """INSERT INTO document_selection_history(document_id,species,enabled,actor)
          VALUES(%s,%s,%s,%s)""",
            (document_id, species, enabled, actor),
        )
        service.event(
            None,
            "selection",
            "Source ajoutée" if enabled else "Source retirée",
            document=document_id,
            data={"species": species, "enabled": enabled, "actor": actor},
            connection=connection,
        )
    return {"id": document_id, "species": links(document_id)}


def listing(
    species: str | None,
    selected_only: bool,
    status: str | None,
    approved_only: bool,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    with service.transaction() as connection:
        return connection.execute(
            f"""SELECT d.*,
          (SELECT coalesce(jsonb_agg(jsonb_build_object('species',s.species,'enabled',s.enabled,
             'available',s.enabled AND {READY})), '[]'::jsonb)
           FROM document_species s WHERE s.document_id=d.id) AS species_links
          FROM scientific_documents d WHERE d.merged_into IS NULL
          AND (%s::text IS NULL OR d.status=%s)
          AND (NOT %s OR ({READY}))
          AND (%s::text IS NULL OR EXISTS(SELECT 1 FROM document_species s
                WHERE s.document_id=d.id AND s.species=%s))
          AND (NOT %s OR (({READY}) AND EXISTS(SELECT 1 FROM document_species s
                WHERE s.document_id=d.id AND s.enabled AND (%s::text IS NULL OR s.species=%s))))
          ORDER BY d.updated_at DESC,d.id LIMIT %s OFFSET %s""",
            (
                status,
                status,
                approved_only,
                species,
                species,
                selected_only,
                species,
                species,
                limit,
                offset,
            ),
        ).fetchall()
