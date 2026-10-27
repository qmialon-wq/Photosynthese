"""Real PostgreSQL authorization and credential lifecycle, no ML or production accounts."""

import importlib.util
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

from shared import accounts
from shared.review.database import jsonb, transaction

pytestmark = pytest.mark.integration
PASSWORD = "phrase-de-passe-test-2026"


class Counters:
    def __init__(self):
        self.values = {}

    def eval(self, script, count, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def close(self):
        pass


@pytest.fixture
def clients(document_db, monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "auth_migration", Path("backend/migrations/versions/0012_authentication.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with transaction() as c:
        monkeypatch.setattr(migration.op, "execute", c.execute)
        migration.upgrade()
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    with TestClient(app) as admin, TestClient(app) as alice, TestClient(app) as bob:
        app.state.redis = Counters()
        yield admin, alice, bob


def signup(client, email="alice@example.test"):
    response = client.post(
        "/auth/register", json={"email": email, "display_name": "Profil test", "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()["user"]


def initialize(admin):
    response = admin.post(
        "/auth/setup",
        json={
            "email": "admin@example.test",
            "display_name": "Admin",
            "password": PASSWORD,
            "setup_token": accounts.bootstrap_file().read_text(),
        },
    )
    assert response.status_code == 201, response.text
    admin.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()["user"]


def test_bootstrap_anonymous_and_registration_role(clients):
    admin, alice, bob = clients
    for path in ("/console/videos", "/documents", "/admin/users", "/review/samples", "/auth/me"):
        assert alice.get(path, headers={"X-Reviewer": "admin"}).status_code == 401
    assert (
        alice.post(
            "/auth/register",
            json={"email": "a@example.test", "display_name": "A", "password": PASSWORD},
        ).status_code
        == 409
    )
    assert (
        alice.post(
            "/auth/setup",
            json={
                "email": "a@example.test",
                "display_name": "A",
                "password": PASSWORD,
                "setup_token": "invalid",
            },
        ).status_code
        == 403
    )
    initialize(admin)
    assert not accounts.bootstrap_file().exists()
    assert (
        alice.post(
            "/auth/register",
            json={
                "email": "a@example.test",
                "display_name": "A",
                "password": PASSWORD,
                "role": "admin",
            },
        ).status_code
        == 422
    )
    signup(alice)
    assert alice.get("/auth/me").json()["user"]["role"] == "client"
    for path in ("/admin/users", "/console/dashboard", "/review/datasets", "/documents/watches"):
        assert alice.get(path).status_code == 403
    assert alice.post("/console/videos/local", json={"video": "existing.mp4"}).status_code == 403
    assert alice.post("/rag/prepare").status_code == 403
    assert (
        admin.patch(
            f"/admin/users/{admin.get('/auth/me').json()['user']['id']}/role",
            json={"role": "client"},
        ).status_code
        == 409
    )


def test_csrf_origin_expiry_and_secure_cookies(clients, monkeypatch):
    admin, alice, bob = clients
    initialize(admin)
    signup(alice)
    assert alice.post("/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert alice.post("/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert (
        bob.post(
            "/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "alice@example.test", "password": PASSWORD},
        ).status_code
        == 403
    )
    with transaction() as c:
        c.execute(
            "UPDATE auth_sessions SET last_seen_at=now()-interval '3 hours' WHERE user_id=%s",
            (alice.get("/auth/me").json()["user"]["id"],),
        )
    assert alice.get("/console/tasks").status_code == 401
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    response = bob.post("/auth/login", json={"email": "alice@example.test", "password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "password" not in response.json()["user"]


def test_ownership_before_pagination_and_job_inputs(clients):
    admin, alice, bob = clients
    initialize(admin)
    a, b = signup(alice), signup(bob, "bob@example.test")
    for path in ("/review/videos", "/review/samples", "/documents/tasks", "/console/models"):
        response = alice.get(path)
        assert response.status_code == 200 and response.json() == [], response.text
    from uuid import uuid4

    with transaction() as c:
        for owner, video, sha in (
            (a["id"], "video-alice", "a" * 64),
            (b["id"], "video-bob", "b" * 64),
        ):
            c.execute(
                "INSERT INTO console_videos(id,filename,video_key,sha256,metadata) "
                "VALUES(%s,%s,'inbox/test.mp4',%s,'{}')",
                (video, video + ".mp4", sha),
            )
            c.execute(
                "INSERT INTO console_tasks(id,kind,actor,request,status,result) "
                "VALUES(%s,'import_upload',%s,'{}','completed',%s)",
                (uuid4(), owner, jsonb({"video_id": video})),
            )
    assert [v["id"] for v in alice.get("/console/videos?limit=1").json()] == ["video-alice"]
    assert len(admin.get("/console/videos").json()) == 2
    foreign_task = bob.get("/console/tasks").json()[0]["id"]
    for path in (
        "/console/videos/video-bob",
        "/console/videos/video-bob/file",
        f"/console/tasks/{foreign_task}",
        f"/console/tasks/{foreign_task}/logs",
    ):
        assert alice.get(path).status_code == 404
    assert alice.post("/console/videos/video-bob/analyze", json={}).status_code == 404
    assert alice.post("/parcels/corpora", json={"video_ids": ["video-bob"]}).status_code == 404
    for media_type in ("application/vnd.api+json", ""):
        assert (
            alice.post(
                "/parcels/corpora",
                content='{"video_ids":["video-bob"]}',
                headers={"Content-Type": media_type},
            ).status_code
            == 404
        )
    assert (
        alice.post(
            "/rag/recommendations", json={"question": "Aménagement", "video_ids": ["video-bob"]}
        ).status_code
        == 404
    )
    assert (
        alice.post("/parcels/import-status", json={"task_ids": [foreign_task]}).status_code == 404
    )
    corpus = alice.post("/parcels/corpora", json={"video_ids": ["video-alice"]})
    assert corpus.status_code == 201, corpus.text
    assert bob.get("/parcels/corpora").json() == []
    assert bob.get(f"/parcels/corpora/{corpus.json()['id']}").status_code == 404
    from shared.documents import service as documents

    own_task = documents.submit("search", {"query": "propre"}, a["id"])
    other_task = documents.submit("search", {"query": "autre"}, b["id"])
    assert [t["id"] for t in alice.get("/documents/tasks").json()] == [own_task["id"]]
    assert alice.get(f"/documents/tasks/{other_task['id']}").status_code == 404
    export = alice.get("/auth/me/export")
    assert export.status_code == 200, export.text
    assert "video-bob" not in export.text and "password_hash" not in export.text


def test_password_reset_deletion_and_revocation(clients):
    admin, alice, bob = clients
    administrator = initialize(admin)
    a = signup(alice)
    login = bob.post("/auth/login", json={"email": a["email"], "password": PASSWORD})
    bob.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (
        alice.post(
            "/auth/password",
            json={"current_password": "incorrect", "new_password": PASSWORD + "-new"},
        ).status_code
        == 403
    )
    assert (
        alice.post(
            "/auth/password", json={"current_password": PASSWORD, "new_password": PASSWORD + "-new"}
        ).status_code
        == 204
    )
    assert bob.get("/auth/me").status_code == 401
    link = admin.post(f"/admin/users/{a['id']}/reset-link").json()["path"]
    token = link.split("token=")[1]
    assert (
        alice.post("/auth/reset-password", json={"token": token, "password": PASSWORD}).status_code
        == 204
    )
    assert (
        alice.post("/auth/reset-password", json={"token": token, "password": PASSWORD}).status_code
        == 400
    )
    login = alice.post("/auth/login", json={"email": a["email"], "password": PASSWORD})
    alice.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert admin.delete(f"/admin/users/{administrator['id']}").status_code == 409
    deleted = alice.request(
        "DELETE", "/auth/me", json={"current_password": PASSWORD, "confirmation": "SUPPRIMER"}
    )
    assert deleted.status_code == 200, deleted.text
    assert alice.get("/auth/me").status_code == 401
    assert (
        bob.post("/auth/login", json={"email": a["email"], "password": PASSWORD}).status_code == 401
    )
    with transaction() as c:
        row = c.execute("SELECT * FROM app_users WHERE id=%s", (a["id"],)).fetchone()
        assert row["deleted_at"] and row["email"] is None and row["password_hash"] is None
        assert (
            c.execute(
                "SELECT count(*) AS n FROM auth_sessions WHERE user_id=%s", (a["id"],)
            ).fetchone()["n"]
            == 0
        )
    assert admin.get("/admin/erasure-requests").json()[0]["id"] == deleted.json()["erasure_request"]


def test_login_rate_limit_and_role_revocation(clients):
    admin, alice, bob = clients
    initialize(admin)
    a = signup(alice)
    for _ in range(11):
        assert (
            bob.post("/auth/login", json={"email": a["email"], "password": "wrong"}).status_code
            == 401
        )
    assert (
        bob.post("/auth/login", json={"email": a["email"], "password": PASSWORD}).status_code == 429
    )
    assert admin.patch(f"/admin/users/{a['id']}/role", json={"role": "admin"}).status_code == 200
    assert alice.get("/auth/me").status_code == 401


def test_profile_credentials_email_and_session_revocation(clients):
    admin, alice, bob = clients
    initialize(admin)
    a = signup(alice)
    login = bob.post("/auth/login", json={"email": a["email"], "password": PASSWORD})
    assert login.status_code == 200
    body = {"email": "nouvelle@example.test", "display_name": "Camille"}
    assert alice.patch("/auth/me", json=body).status_code == 403
    assert alice.patch("/auth/me", json={**body, "role": "admin"}).status_code == 422
    saved = alice.patch("/auth/me", json={**body, "current_password": PASSWORD})
    assert saved.status_code == 200, saved.text
    assert saved.json()["email"] == body["email"]
    assert bob.get("/auth/me").status_code == 401
    assert alice.get("/auth/me").status_code == 200
    assert alice.patch("/auth/me", json={**body, "display_name": "   "}).status_code == 422
    with transaction() as c:
        c.execute(
            "UPDATE auth_sessions SET expires_at=now()-interval '1 second' WHERE user_id=%s",
            (a["id"],),
        )
    assert alice.get("/auth/me").status_code == 401
