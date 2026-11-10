"""Durable territorial consultations, independent of RAG generation and video inference."""

import logging

from shared.documents import service as documents
from shared.parcels.territorial_schemas import Analysis
from shared.review.database import jsonb, transaction
from workers.documents import ign


def build(identifier: str) -> dict:
    with transaction() as c:
        row = c.execute("SELECT * FROM territorial_queries WHERE id=%s", (identifier,)).fetchone()
    if not row:
        raise ValueError("Consultation territoriale inconnue")
    if row["result"]:
        return {"query_id": identifier, "status": ign.status(row["layers"])}

    def persist(layers):
        with transaction() as c:
            c.execute(
                "UPDATE territorial_queries SET layers=%s WHERE id=%s", (jsonb(layers), identifier)
            )

    layers = ign.collect(row["inputs"]["location"], row["layers"], persist)
    from shared.parcels.territorial_rules import analyze

    result = Analysis.model_validate(analyze(row["inputs"], layers, row["revision"])).model_dump()
    with transaction() as c:
        c.execute(
            "UPDATE territorial_queries SET layers=%s,result=%s,finished_at=now() WHERE id=%s",
            (jsonb(layers), jsonb(result), identifier),
        )
    # Publish the deterministic result first; documentary scheduling cannot invalidate IGN.
    try:
        documents.submit(
            "territorial_evidence",
            {"query_id": identifier},
            row["actor"],
            dedup_key=f"territorial-evidence:{identifier}",
        )
    except Exception:
        logging.getLogger(__name__).exception("Complément documentaire non programmé")
    return {"query_id": identifier, "status": ign.status(layers)}
