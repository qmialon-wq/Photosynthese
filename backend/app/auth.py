"""Authentication and account administration. No password or token goes to audit logs."""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from redis.exceptions import RedisError

from shared import accounts
from shared.access import video_ids
from shared.review.database import ReviewError, transaction

router = APIRouter(tags=["accounts"])


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Body):
    email: str = Field(max_length=254)
    password: SecretStr


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=100)


class Setup(Registration):
    setup_token: SecretStr


class Profile(Body):
    display_name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254)
    current_password: SecretStr | None = None


class Password(Body):
    current_password: SecretStr
    new_password: SecretStr


class Deletion(Body):
    current_password: SecretStr
    confirmation: Literal["SUPPRIMER"]


class AdminCreate(Registration):
    role: Literal["client", "admin"] = "client"


class Role(Body):
    role: Literal["client", "admin"]


class Reset(Body):
    token: SecretStr
    password: SecretStr


class ErasureReview(Body):
    status: Literal["processing", "completed"]
    note: str = Field(min_length=20, max_length=4000)


def user(request: Request) -> dict[str, Any]:
    return request.state.user


def limit(request: Request, identifier: str) -> None:
    # Atomic Redis counters; ignore untrusted forwarding headers.
    peer = request.client.host if request.client else "unknown"
    for key, maximum in (("ip:" + peer, 60), ("account:" + identifier.lower(), 12)):
        key = "auth-limit:" + accounts.digest(key)
        try:
            count = request.app.state.redis.eval(
                "local n=redis.call('INCR',KEYS[1]); if n==1 then "
                "redis.call('EXPIRE',KEYS[1],600) end; return n",
                1,
                key,
            )
        except RedisError:
            raise ReviewError("Authentification temporairement indisponible", 503) from None
        if count > maximum:
            raise ReviewError("Trop de tentatives ; réessayez dans quelques minutes", 429)


def session_response(response: Response, row: dict[str, Any]) -> dict[str, Any]:
    verified = row.pop("_verified_hash", None)
    token = accounts.new_session(row["id"], verified)
    response.set_cookie(
        accounts.COOKIE,
        token,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true",
        samesite="lax",
        max_age=12 * 3600,
        path="/",
    )
    return {"user": row, "csrf_token": accounts.csrf(token)}


@router.get("/auth/status")
def status():
    with transaction() as c:
        ready = c.execute(
            "SELECT 1 FROM app_users WHERE role='admin' AND deleted_at IS NULL"
        ).fetchone()
    return {"setup_required": not bool(ready), "registration_open": bool(ready)}


@router.post("/auth/setup", status_code=201)
def setup(body: Setup, request: Request, response: Response):
    limit(request, "bootstrap")
    row = accounts.create_user(
        body.email,
        body.display_name,
        body.password.get_secret_value(),
        setup_token=body.setup_token.get_secret_value(),
    )
    return session_response(response, row)


@router.post("/auth/register", status_code=201)
def register(body: Registration, request: Request, response: Response):
    limit(request, body.email)
    row = accounts.create_user(body.email, body.display_name, body.password.get_secret_value())
    return session_response(response, row)


@router.post("/auth/login")
def login(body: Credentials, request: Request, response: Response):
    limit(request, body.email)
    return session_response(response, accounts.login(body.email, body.password.get_secret_value()))


@router.get("/auth/me")
def me(request: Request):
    return {"user": user(request), "csrf_token": accounts.csrf(request.cookies[accounts.COOKIE])}


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    with transaction() as c:
        c.execute(
            "DELETE FROM auth_sessions WHERE token_hash=%s",
            (accounts.digest(request.cookies[accounts.COOKIE]),),
        )
    response.delete_cookie(accounts.COOKIE, path="/")


@router.patch("/auth/me")
def profile(body: Profile, request: Request):
    current = user(request)
    email = accounts.email_address(body.email)
    name = body.display_name.strip()
    if email != current["email"]:
        limit(request, "credentials:" + current["id"])
    if not name:
        raise ReviewError("Nom de profil requis", 422)
    try:
        with transaction() as c:
            if email != current["email"]:
                accounts.check_password(
                    current["id"],
                    body.current_password.get_secret_value() if body.current_password else "",
                    c,
                )
                c.execute(
                    "DELETE FROM auth_sessions WHERE user_id=%s AND token_hash<>%s",
                    (current["id"], accounts.digest(request.cookies[accounts.COOKIE])),
                )
            row = c.execute(
                f"""UPDATE app_users SET email=%s,display_name=%s,updated_at=now()
              WHERE id=%s AND deleted_at IS NULL RETURNING {accounts.PUBLIC_FIELDS}""",
                (email, name, current["id"]),
            ).fetchone()
            if not row:
                raise ReviewError("Compte indisponible", 401)
            accounts.audit(c, "profile_updated", current["id"], current["id"])
    except UniqueViolation:
        raise ReviewError("Cette adresse ne peut pas être utilisée", 409) from None
    return row


@router.post("/auth/password", status_code=204)
def password(body: Password, request: Request, response: Response):
    current = user(request)
    limit(request, "credentials:" + current["id"])
    encoded = accounts.hash_password(body.new_password.get_secret_value())
    with transaction() as c:
        accounts.check_password(current["id"], body.current_password.get_secret_value(), c)
        c.execute(
            "UPDATE app_users SET password_hash=%s,updated_at=now() WHERE id=%s AND "
            "deleted_at IS NULL",
            (encoded, current["id"]),
        )
        c.execute("DELETE FROM auth_sessions WHERE user_id=%s", (current["id"],))
        c.execute("DELETE FROM auth_password_resets WHERE user_id=%s", (current["id"],))
        accounts.audit(c, "password_changed", current["id"], current["id"])
    response.delete_cookie(accounts.COOKIE, path="/")


@router.delete("/auth/me")
def delete_me(body: Deletion, request: Request, response: Response):
    current = user(request)
    limit(request, "credentials:" + current["id"])
    reference = accounts.delete_account(
        current["id"], current["id"], body.current_password.get_secret_value()
    )
    response.delete_cookie(accounts.COOKIE, path="/")
    return {"erasure_request": reference, "status": "pending"}


@router.get("/auth/me/export")
def export_me(request: Request):
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse

    current = user(request)
    with transaction() as c:
        actor = current["id"]
        videos = video_ids(c, actor)
        data = {
            "profile": current,
            "videos": c.execute(
                "SELECT * FROM console_videos WHERE id=ANY(%s)", (videos,)
            ).fetchall(),
            "dossiers": c.execute(
                "SELECT * FROM parcel_dossiers WHERE actor=%s", (actor,)
            ).fetchall(),
            "profiles": c.execute(
                "SELECT * FROM parcel_corpus_profiles WHERE actor=%s", (actor,)
            ).fetchall(),
            "video_profiles": c.execute(
                "SELECT * FROM parcel_profiles WHERE actor=%s", (actor,)
            ).fetchall(),
            "tasks": c.execute("SELECT * FROM console_tasks WHERE actor=%s", (actor,)).fetchall(),
            "decisions": c.execute(
                "SELECT * FROM review_revisions WHERE actor=%s", (actor,)
            ).fetchall(),
        }
        # These tables contain user-supplied questions, names and import metadata too.
        for table in (
            "document_tasks",
            "rag_runs",
            "parcel_corpora",
            "console_uploads",
            "review_imports",
            "review_operations",
            "rag_video_context",
            "rag_context_history",
            "document_reviews",
            "document_selection_history",
        ):
            data[table] = c.execute(f"SELECT * FROM {table} WHERE actor=%s", (actor,)).fetchall()
    return JSONResponse(
        jsonable_encoder(data),
        headers={"Content-Disposition": 'attachment; filename="mes-donnees.json"'},
    )


@router.get("/admin/users")
def users(q: str = "", include_deleted: bool = False):
    with transaction() as c:
        return c.execute(
            f"""SELECT {accounts.PUBLIC_FIELDS} FROM app_users
          WHERE (email ILIKE %s OR display_name ILIKE %s) AND (%s OR deleted_at IS NULL)
          ORDER BY created_at DESC LIMIT 200""",
            (f"%{q}%", f"%{q}%", include_deleted),
        ).fetchall()


@router.post("/admin/users", status_code=201)
def create(body: AdminCreate, request: Request):
    return accounts.create_user(
        body.email,
        body.display_name,
        body.password.get_secret_value(),
        body.role,
        actor=user(request)["id"],
    )


@router.patch("/admin/users/{identifier}/role")
def role(identifier: UUID, body: Role, request: Request):
    with transaction() as c:
        if body.role == "client":
            accounts.protect_last_admin(c, identifier)
        else:
            c.execute("SELECT pg_advisory_xact_lock(%s)", (accounts.LOCK,))
        row = c.execute(
            f"""UPDATE app_users SET role=%s,updated_at=now()
          WHERE id=%s AND deleted_at IS NULL RETURNING {accounts.PUBLIC_FIELDS}""",
            (body.role, identifier),
        ).fetchone()
        if not row:
            raise ReviewError("Compte introuvable", 404)
        c.execute("DELETE FROM auth_sessions WHERE user_id=%s", (identifier,))
        accounts.audit(c, "role_changed", user(request)["id"], identifier)
    return row


@router.delete("/admin/users/{identifier}")
def delete_user(identifier: UUID, request: Request):
    return {"erasure_request": accounts.delete_account(str(identifier), user(request)["id"])}


@router.post("/admin/users/{identifier}/reset-link")
def reset_link(identifier: UUID, request: Request):
    token = secrets.token_urlsafe(32)
    with transaction() as c:
        if not c.execute(
            "SELECT 1 FROM app_users WHERE id=%s AND deleted_at IS NULL FOR UPDATE", (identifier,)
        ).fetchone():
            raise ReviewError("Compte introuvable", 404)
        c.execute(
            "DELETE FROM auth_password_resets WHERE user_id=%s OR expires_at<now()", (identifier,)
        )
        c.execute(
            "INSERT INTO auth_password_resets VALUES(%s,%s,%s)",
            (accounts.digest(token), identifier, datetime.now(UTC) + timedelta(minutes=30)),
        )
        accounts.audit(c, "password_reset_issued", user(request)["id"], identifier)
    return {"path": "/reinitialiser#token=" + token, "expires_in_minutes": 30}


@router.post("/auth/reset-password", status_code=204)
def reset(body: Reset, request: Request):
    limit(request, "reset:" + accounts.digest(body.token.get_secret_value()))
    encoded = accounts.hash_password(body.password.get_secret_value())
    with transaction() as c:
        candidate = c.execute(
            "SELECT user_id FROM auth_password_resets WHERE token_hash=%s",
            (accounts.digest(body.token.get_secret_value()),),
        ).fetchone()
        if (
            not candidate
            or not c.execute(
                "SELECT 1 FROM app_users WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
                (candidate["user_id"],),
            ).fetchone()
        ):
            raise ReviewError("Lien expiré ou déjà utilisé", 400)
        # Lock the user before the reset row, as do deletion and password changes.
        row = c.execute(
            """SELECT r.user_id FROM auth_password_resets r JOIN app_users u ON u.id=r.user_id
          WHERE token_hash=%s AND expires_at>now() AND u.deleted_at IS NULL FOR UPDATE OF r,u""",
            (accounts.digest(body.token.get_secret_value()),),
        ).fetchone()
        if not row:
            raise ReviewError("Lien expiré ou déjà utilisé", 400)
        c.execute(
            "UPDATE app_users SET password_hash=%s,updated_at=now() WHERE id=%s",
            (encoded, row["user_id"]),
        )
        c.execute("DELETE FROM auth_sessions WHERE user_id=%s", (row["user_id"],))
        c.execute("DELETE FROM auth_password_resets WHERE user_id=%s", (row["user_id"],))
        accounts.audit(c, "password_reset", row["user_id"], row["user_id"])


@router.get("/admin/erasure-requests")
def erasure_requests():
    with transaction() as c:
        return c.execute(
            "SELECT * FROM auth_erasure_requests ORDER BY requested_at DESC LIMIT 200"
        ).fetchall()


@router.patch("/admin/erasure-requests/{identifier}")
def erasure_review(identifier: UUID, body: ErasureReview, request: Request):
    with transaction() as c:
        row = c.execute(
            """UPDATE auth_erasure_requests SET status=%s,note=%s,reviewed_at=now(),reviewed_by=%s
          WHERE id=%s RETURNING *""",
            (body.status, body.note, user(request)["id"], identifier),
        ).fetchone()
        if not row:
            raise ReviewError("Demande introuvable", 404)
        accounts.audit(c, "erasure_reviewed", user(request)["id"], row["user_id"])
    return row
