"""Opt-in real IGN worker proof; all accounts/corpora stay in a temporary SQL schema."""

import gzip
import json
import os
from pathlib import Path

import pytest

from shared.review.database import transaction
from tests.documents.test_authentication import clients  # noqa: F401
from tests.documents.test_territorial import parcel  # noqa: F401
from workers.documents.runtime import execute

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("TERRITORIAL_LIVE") != "1", reason="IGN live opt-in"),
]


def test_real_normandy_points_through_worker(parcel, document_db):  # noqa: F811
    alice, _, path = parcel
    archives = []
    for index, (name, latitude, longitude) in enumerate(
        [
            ("caen", 49.1829, -0.3707),
            ("carentan", 49.316, -1.235),
        ]
    ):
        saved = alice.put(
            path + "/location",
            json={"latitude": latitude, "longitude": longitude, "expected_revision": index},
        )
        assert saved.status_code == 200, saved.text
        created = alice.post(
            path + "/territorial-queries",
            json={"expected_location_revision": index + 1, "expected_profile_revision": 0},
        )
        assert created.status_code == 202, created.text
        with transaction() as c:
            task = c.execute(
                "SELECT task_id FROM territorial_queries WHERE id=%s", (created.json()["id"],)
            ).fetchone()["task_id"]
        assert execute(str(task), document_db)
        result = alice.get(path + "/territorial-context/export").json()
        # Export public map evidence only, never test session/account identifiers.
        archive = {
            "mode": "archive",
            "origin": "direct IGN via document worker",
            "place": name,
            "location": {"latitude": latitude, "longitude": longitude},
            "created_at": result["created_at"],
            "status": result["status"],
            "layers": result["layers"],
        }
        archives.append(archive)
        if os.getenv("TERRITORIAL_EVIDENCE_DIR"):
            Path(os.environ["TERRITORIAL_EVIDENCE_DIR"], name + ".json.gz").write_bytes(
                gzip.compress(json.dumps(archive, ensure_ascii=False, indent=2).encode(), mtime=0)
            )
    assert all(a["status"] in ("complete", "partial", "failed") for a in archives)
