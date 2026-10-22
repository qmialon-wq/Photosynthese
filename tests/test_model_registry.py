import hashlib
from uuid import uuid4

import pytest
from biosentinelle_vision.classes import load_classes
from biosentinelle_vision.datasets.benchmark import canonical
from test_console import console_db  # noqa: F401
from test_promotion import example

from shared import console
from shared.promotion import promote, rollback
from shared.review.database import ReviewError, jsonb, transaction

pytest_plugins = ["test_review_integration"]
pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("console_db")
def test_candidate_cannot_activate_without_comparison_and_rollback_is_audited():
    champion, candidate, comparison_id = str(uuid4()), str(uuid4()), str(uuid4())
    report = example()
    report["classes"] = load_classes().model_dump(mode="json")
    for row, identifier, checksum in zip(
        report["models"], [champion, candidate], ["a" * 64, "b" * 64], strict=True
    ):
        row["model"]["model_id"] = identifier
        row["checkpoint_sha256"] = checksum
    with transaction() as connection:
        for identifier, checksum, active in [
            (champion, "a" * 64, True),
            (candidate, "b" * 64, False),
        ]:
            connection.execute(
                """INSERT INTO console_models
              (id,name,checkpoint_key,sha256,metadata,metrics,actor,active,status)
              VALUES(%s,'test','test.pt',%s,%s,'{}','test',%s,%s)""",
                (
                    identifier,
                    checksum,
                    jsonb({"classes": report["classes"]}),
                    active,
                    "active" if active else "candidate",
                ),
            )
        connection.execute(
            """INSERT INTO classifier_comparisons(id,report,report_sha256,actor)
          VALUES(%s,%s,%s,'test')""",
            (comparison_id, jsonb(report), hashlib.sha256(canonical(report)).hexdigest()),
        )
    with pytest.raises(ReviewError, match="Comparer"):
        console.activate_model(candidate)
    decision = promote(candidate, comparison_id, "test")
    assert decision["activated"] is False
    decision = promote(
        candidate, comparison_id, "test", manual_reason="Examen humain du petit échantillon"
    )
    assert decision["activated"] is True
    assert rollback(champion, "test", "Retour au champion précédent")["active"]
    with transaction() as connection:
        assert (
            str(connection.execute("SELECT id FROM console_models WHERE active").fetchone()["id"])
            == champion
        )
        assert connection.execute("SELECT count(*) AS n FROM model_promotions").fetchone()["n"] == 3
