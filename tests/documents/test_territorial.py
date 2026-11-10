import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest

from shared.review.database import transaction
from tests.documents.test_authentication import clients, initialize, signup  # noqa: F401
from tests.test_territorial_contracts import PROFILE

pytestmark = pytest.mark.integration


@pytest.fixture
def parcel(clients, monkeypatch):  # noqa: F811
    admin, alice, bob = clients
    initialize(admin)
    owner = signup(alice)
    signup(bob, "bob@example.test")
    spec = importlib.util.spec_from_file_location(
        "territorial_migration", Path("backend/migrations/versions/0013_territorial_context.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    identifier = str(uuid4())
    with transaction() as c:
        monkeypatch.setattr(migration.op, "execute", c.execute)
        migration.upgrade()
        c.execute("INSERT INTO parcel_corpora(id,actor) VALUES(%s,%s)", (identifier, owner["id"]))
    return alice, bob, f"/parcels/corpora/{identifier}"


def test_persistence_conflicts_and_real_session_permissions(parcel):
    alice, bob, path = parcel
    response = alice.put(path + "/profile", json=PROFILE)
    assert response.status_code == 200, response.text
    assert "interventions" not in response.json()["profile"]
    body = {**PROFILE, "interventions": ["fencing"], "expected_revision": 1}
    assert alice.put(path + "/profile", json=body).json()["revision"] == 2
    saved = alice.put(path + "/profile", json={**PROFILE, "expected_revision": 2})
    assert saved.json()["profile"]["interventions"] == ["fencing"]
    assert alice.put(path + "/profile", json=body).status_code == 409
    assert (
        alice.put(
            path + "/profile", json={**body, "expected_revision": 2, "interventions": []}
        ).json()["revision"]
        == 3
    )
    location = {"latitude": 49.18, "longitude": -0.36, "expected_revision": 0}
    result = alice.put(path + "/location", json=location)
    assert result.status_code == 200, result.text
    assert result.json()["revision"] == 1
    assert alice.put(path + "/location", json=location).status_code == 409
    assert alice.put(path + "/location", json={**location, "latitude": 91}).status_code == 422
    for suffix in ("", "/territorial-context", "/territorial-context/export"):
        assert bob.get(path + suffix).status_code == 404
    for suffix, body in (("/location", location), ("/profile", PROFILE)):
        assert bob.put(path + suffix, json=body).status_code == 404
        assert alice.put(path + suffix, json=body, headers={"X-CSRF-Token": ""}).status_code == 403
        assert (
            alice.put(
                path + suffix, json=body, headers={"Origin": "https://foreign.test"}
            ).status_code
            == 403
        )
    from shared.parcels.territorial import location as read_location

    with transaction() as c:
        assert read_location(c, path.split("/")[-1])["longitude"] == -0.36


def test_queries_export_obsolescence_and_worker_resume(parcel, document_db, monkeypatch):
    alice, bob, path = parcel
    from workers.documents import ign
    from workers.documents.runtime import execute

    alice.put(path + "/profile", json={**PROFILE, "interventions": ["earthworks"]})
    alice.put(
        path + "/location", json={"latitude": 49.18, "longitude": -0.36, "expected_revision": 0}
    )
    body = {"expected_location_revision": 1, "expected_profile_revision": 1}
    created = alice.post(path + "/territorial-queries", json=body)
    assert created.status_code == 202, created.text
    assert alice.post(path + "/territorial-queries", json=body).json()["id"] == created.json()["id"]
    assert bob.post(path + "/territorial-queries", json=body).status_code == 404
    assert bob.get(path + "/territorial-context").status_code == 404
    assert bob.get(path + "/territorial-context/export").status_code == 404
    assert alice.get(path + "/territorial-context").json()["query"]["status"] == "pending"
    assert alice.get(path + "/territorial-context/export").status_code == 409

    def collect(location, completed, persist):
        result = {
            layer: {
                "layer": layer,
                "status": "empty",
                "features": [],
                "source_url": ign.BASE + layer,
                "retrieved_at": "2026-11-10T12:00:00Z",
                "raw_response": '{"type":"FeatureCollection","features":[]}',
            }
            for layer in ign.LAYERS
        }
        persist(result)
        return result

    monkeypatch.setattr(ign, "collect", collect)
    with transaction() as c:
        row = c.execute(
            "SELECT * FROM territorial_queries WHERE id=%s", (created.json()["id"],)
        ).fetchone()
        task = str(row["task_id"])
        c.execute("UPDATE document_tasks SET status='running' WHERE id=%s", (task,))
    from shared.task_priority import recover_interrupted

    recover_interrupted("documents")
    assert execute(task, document_db)
    assert execute(task, document_db)  # Idempotent completion.
    result = alice.get(path + "/territorial-context").json()["query"]
    assert result["status"] == "complete" and not result["obsolete"]
    exported = alice.get(path + "/territorial-context/export").json()
    assert exported["inputs"]["profile"]["interventions"] == ["earthworks"]
    alice.put(
        path + "/profile", json={**PROFILE, "interventions": ["fencing"], "expected_revision": 1}
    )
    result = alice.get(path + "/territorial-context").json()["query"]
    assert result["obsolete"] and result["inputs"]["profile"]["interventions"] == ["earthworks"]
    assert alice.post(path + "/territorial-queries", json=body).status_code == 409
    body["expected_profile_revision"] = 2
    assert alice.post(path + "/territorial-queries", json=body).status_code == 202
    archived = alice.get(path + "/territorial-context?revision=1").json()["query"]
    assert archived["id"] == created.json()["id"] and archived["obsolete"]


def test_limited_intervention_editor_preserves_profile_and_absent_fields(parcel):
    alice, _, path = parcel
    initial = alice.put(
        path + "/profile", json={"interventions": ["fencing"], "expected_revision": 0}
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["profile"] == {"interventions": ["fencing"]}
    full = alice.put(
        path + "/profile",
        json={**PROFILE, "details": "Conserver ces précisions", "expected_revision": 1},
    )
    assert full.json()["profile"]["interventions"] == ["fencing"]
    patch = alice.put(path + "/profile", json={"interventions": [], "expected_revision": 2})
    assert patch.json()["profile"] == {**full.json()["profile"], "interventions": []}
    assert alice.post(path + "/dossiers", json={"profile_revision": 1}).status_code == 422
    assert (
        alice.put(
            path + "/profile", json={"interventions": None, "expected_revision": 3}
        ).status_code
        == 422
    )
    assert (
        alice.put(
            path + "/profile", json={"interventions": ["invented"], "expected_revision": 3}
        ).status_code
        == 422
    )


def test_ab_through_redis_worker_and_observation_revision(parcel, document_db, monkeypatch):
    """Synthetic observation fixture; real sessions, SQL, Redis and deterministic worker."""
    import os

    from redis import Redis

    from workers.documents import ign, runtime

    alice, _, path = parcel
    identifier = path.split("/")[-1]
    owner = alice.get("/auth/me").json()["user"]["id"]
    with transaction() as c:
        c.execute("INSERT INTO review_groups(id,split) VALUES('fixture','train')")
        c.execute(
            "INSERT INTO review_videos(id,group_id,source_key,original_name,candidates) "
            "VALUES('fixture','fixture','test.mp4','Fixture synthétique.mp4','[]')"
        )
        c.execute(
            "INSERT INTO review_imports(id,video_id,original_name,actor,provenance) "
            "VALUES(%s,'fixture','Fixture synthétique.mp4',%s,'{}')",
            (uuid4(), owner),
        )
        c.execute(
            "INSERT INTO review_frames VALUES('frame','fixture',1,0,'test.jpg','sha',100,100,'{}')"
        )
        for sample, state, label in [
            ("human", "validated", "blaireaux"),
            ("predicted", "pending", None),
        ]:
            c.execute(
                "INSERT INTO review_samples(id,frame_id,original_box,original_crop_key,"
                "detector_identity,detection_score,predicted_label,current_revision) "
                "VALUES(%s,'frame','{}','test.jpg','synthetic-test',0.9,'blaireaux',1)",
                (sample,),
            )
            c.execute(
                "INSERT INTO review_revisions(sample_id,revision,state,label,box,recipe,"
                "render_status,actor,provenance) VALUES(%s,1,%s,%s,'{}','{}','ready',%s,'{}')",
                (sample, state, label, owner),
            )
        c.execute(
            "INSERT INTO parcel_corpus_videos VALUES(%s,'fixture','sha','Fixture.mp4',0)",
            (identifier,),
        )
    monkeypatch.setattr(
        ign,
        "collect",
        lambda *args: {
            name: {
                "status": "empty",
                "features": [],
                "source_url": ign.BASE + name,
                "retrieved_at": "2026-11-10T10:00:00Z",
            }
            for name in ign.LAYERS
        },
    )
    stream = "territorial-test:" + uuid4().hex
    monkeypatch.setattr(runtime, "STREAM", stream)
    monkeypatch.setattr(runtime, "GROUP", "territorial-test")
    redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    results = []
    try:
        runtime.ensure_group(redis)
        alice.put(
            path + "/location", json={"latitude": 49.18, "longitude": -0.36, "expected_revision": 0}
        )
        for revision, codes in [(1, ["outdoor_lighting"]), (2, ["outdoor_lighting", "fencing"])]:
            saved = alice.put(
                path + "/profile", json={"interventions": codes, "expected_revision": revision - 1}
            )
            assert saved.status_code == 200, saved.text
            created = alice.post(
                path + "/territorial-queries",
                json={"expected_location_revision": 1, "expected_profile_revision": revision},
            )
            assert created.status_code == 202, created.text
            assert runtime.publish_pending(redis) >= 1
            # All queues in this schema belong to this test; complete the interactive query.
            for _ in range(10):
                runtime.consume_one(redis, document_db)
                current = alice.get(path + "/territorial-context").json()["query"]
                if current["result"]:
                    break
            assert current["status"] == "complete", current
            assert [o["sample_id"] for o in current["inputs"]["observations"]] == ["human"]
            results.append(current)
        a, b = results
        assert [x for x in a["result"]["actions"] if x["project_action"] == "outdoor_lighting"] == [
            x for x in b["result"]["actions"] if x["project_action"] == "outdoor_lighting"
        ]
        fence = next(x for x in b["result"]["actions"] if x["project_action"] == "fencing")
        assert fence["evidence_refs"] == ["project:fencing", "human:human:1"]
        assert fence["category"] == "investigate"
        with transaction() as c:
            c.execute(
                "INSERT INTO review_revisions(sample_id,revision,state,label,box,recipe,"
                "render_status,actor,provenance) "
                "VALUES('human',2,'corrected','renards','{}','{}','ready',%s,'{}')",
                (owner,),
            )
            c.execute("UPDATE review_samples SET current_revision=2 WHERE id='human'")
        current = alice.get(path + "/territorial-context").json()["query"]
        assert current["obsolete"] and current["inputs"]["observations"][0]["revision"] == 1
        assert current["result"]["facts"] == b["result"]["facts"]
    finally:
        redis.delete(stream)
        redis.close()


@pytest.mark.parametrize("document_case", ["absent", "irrelevant", "eligible", "unavailable"])
def test_documentary_optional_independent_and_revisioned(
    parcel, document_db, monkeypatch, document_case
):
    from shared.parcels.service import snapshot_sha
    from shared.parcels.territorial import inputs
    from shared.parcels.territorial_rules import analyze
    from shared.review.database import jsonb
    from tests.documents.test_rag import publication
    from workers.documents import territorial_evidence
    from workers.documents.runtime import execute

    alice, _, path = parcel
    identifier = path.split("/")[-1]
    owner = alice.get("/auth/me").json()["user"]["id"]
    alice.put(
        path + "/profile", json={"interventions": ["outdoor_lighting"], "expected_revision": 0}
    )
    alice.put(
        path + "/location", json={"latitude": 49.18, "longitude": -0.36, "expected_revision": 0}
    )
    layers = {
        name: {
            "status": "empty",
            "features": [],
            "source_url": "https://apicarto.ign.fr",
            "retrieved_at": "2026-11-10T10:00:00Z",
        }
        for name in ("znieff1", "znieff2", "natura-habitat", "natura-oiseaux")
    }
    query_id = str(uuid4())
    with transaction() as c:
        snapshot = inputs(c, identifier)
        # Synthetic frozen observation for this archival/retrieval contract test.
        snapshot["observations"] = [
            {
                "species": "renards",
                "state": "validated",
                "sample_id": "synthetic-documentary-test",
                "revision": 1,
            }
        ]
        original = analyze(snapshot, layers, 1)
        c.execute(
            "INSERT INTO territorial_queries "
            "(id,corpus_id,revision,input_sha256,inputs,layers,result,actor) "
            "VALUES(%s,%s,1,%s,%s,%s,%s,%s)",
            (
                query_id,
                identifier,
                snapshot_sha(snapshot),
                jsonb(snapshot),
                jsonb(layers),
                jsonb(original),
                owner,
            ),
        )
    if document_case == "irrelevant":
        publication("Bartonella infection in a wild carnivore.")
    if document_case == "eligible":
        publication("Artificial lighting changes wildlife activity. Synthetic test fixture.")
        publication("Artificial lighting unrelated unapproved fixture.", approved=False)
    if document_case == "unavailable":
        monkeypatch.setattr(
            territorial_evidence.retrieval,
            "retrieve",
            lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("offline")),
        )
    from shared.documents import service as documents

    task = documents.submit("territorial_evidence", {"query_id": query_id}, owner)
    assert execute(task["id"], document_db)
    current = alice.get(path + "/territorial-context").json()["query"]
    assert current["status"] == "complete"
    assert current["result"]["compensation"] == {"status": "not_assessed"}
    assert all(a["category"] == "investigate" for a in current["result"]["actions"])
    if document_case == "eligible":
        assert current["revision"] == 2
        assert current["result"]["documentary"]["base_query_id"] == query_id
        candidates = [s for s in current["result"]["sources"] if s["id"].startswith("doc:")]
        assert len(candidates) == 1
        assert candidates[0]["applicability"] == "not_assessed"
        assert candidates[0]["page"] == 3 and candidates[0]["text_sha256"]
        assert candidates[0]["relevance_reason"]
        # Replay is idempotent and the first deterministic result stays unchanged.
        assert territorial_evidence.enrich(query_id)["query_id"] == current["id"]
        first = alice.get(path + "/territorial-context?revision=1").json()["query"]
        assert first["result"] == original
    else:
        assert current["revision"] == 1 and current["result"] == original
        task_result = documents.task(task["id"])
        assert task_result["status"] == ("error" if document_case == "unavailable" else "completed")


def test_late_documentary_revision_does_not_hide_new_consultation(parcel, document_db, monkeypatch):
    from workers.documents import ign, territorial_evidence
    from workers.documents.runtime import execute

    alice, _, path = parcel
    alice.put(
        path + "/location", json={"latitude": 49.18, "longitude": -0.36, "expected_revision": 0}
    )
    body = {"expected_location_revision": 1, "expected_profile_revision": 0}
    first = alice.post(path + "/territorial-queries", json=body).json()["id"]
    monkeypatch.setattr(
        ign,
        "collect",
        lambda *args: {
            name: {
                "status": "empty",
                "features": [],
                "source_url": ign.BASE + name,
                "retrieved_at": "2026-11-10T10:00:00Z",
            }
            for name in ign.LAYERS
        },
    )
    with transaction() as c:
        task = c.execute("SELECT task_id FROM territorial_queries WHERE id=%s", (first,)).fetchone()
    assert execute(str(task["task_id"]), document_db)
    second = alice.post(path + "/territorial-queries", json=body).json()["id"]
    monkeypatch.setattr(territorial_evidence, "candidates", lambda _: [{}])
    assert territorial_evidence.enrich(first)["status"] == "superseded"
    current = alice.get(path + "/territorial-context").json()["query"]
    assert current["id"] == second and current["status"] == "pending"
