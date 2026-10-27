"""Local credentials and revocable, opaque sessions; never persist raw session tokens."""

import hashlib
import hmac
import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection

from shared.review.database import ReviewError, transaction

COOKIE = "biosentinelle_session"
PUBLIC_FIELDS = "id,email,display_name,role,created_at,deleted_at"
LOCK = 641728120
PASSWORD_SLOTS = BoundedSemaphore(2)


def password_digest(password: str, salt: bytes) -> bytes:
    # Bound the memory used by concurrent scrypt requests (128 MiB per operation).
    if not PASSWORD_SLOTS.acquire(blocking=False):
        raise ReviewError("Authentification occupée ; réessayez dans quelques instants", 503)
    try:
        return hashlib.scrypt(
            password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024**2, dklen=64
        )
    finally:
        PASSWORD_SLOTS.release()


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def email_address(email: str) -> str:
    value = email.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ReviewError("Adresse e-mail invalide", 422)
    return value


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ReviewError("Le mot de passe doit contenir entre 12 et 1024 caractères", 422)
    salt = secrets.token_bytes(16)
    value = password_digest(password, salt)
    return f"scrypt${salt.hex()}${value.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or len(password) > 1024:
        return False
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = password_digest(password, bytes.fromhex(salt))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def audit(
    connection: Connection,
    action: str,
    actor: str | UUID | None = None,
    target: str | UUID | None = None,
) -> None:
    connection.execute(
        "INSERT INTO auth_events(actor,target,action) VALUES(%s,%s,%s)", (actor, target, action)
    )


def bootstrap_file() -> Path:
    return Path(os.getenv("STORAGE_ROOT", "/storage")) / "results/auth/bootstrap-token"


def ensure_bootstrap() -> None:
    with transaction() as c:
        c.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
        if c.execute(
            "SELECT 1 FROM app_users WHERE role='admin' AND deleted_at IS NULL"
        ).fetchone():
            return
        row = c.execute("SELECT * FROM auth_bootstrap WHERE singleton").fetchone()
        if row:
            return
        path = bootstrap_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            token = path.read_text().strip()
        else:
            token = secrets.token_urlsafe(32)
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(token)
        c.execute("INSERT INTO auth_bootstrap(token_hash) VALUES(%s)", (digest(token),))


def create_user(
    email: str,
    name: str,
    password: str,
    role: str = "client",
    *,
    setup_token: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    email, encoded = email_address(email), hash_password(password)
    name = name.strip()
    if not 1 <= len(name) <= 100:
        raise ReviewError("Nom de profil requis (100 caractères maximum)", 422)
    from psycopg.errors import UniqueViolation

    try:
        with transaction() as c:
            c.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            if setup_token is not None:
                bootstrap = c.execute(
                    "SELECT * FROM auth_bootstrap WHERE singleton FOR UPDATE"
                ).fetchone()
                exists = c.execute(
                    "SELECT 1 FROM app_users WHERE role='admin' AND deleted_at IS NULL"
                ).fetchone()
                if (
                    exists
                    or not bootstrap
                    or bootstrap["consumed_at"]
                    or not hmac.compare_digest(bootstrap["token_hash"], digest(setup_token))
                ):
                    raise ReviewError("Initialisation indisponible ou jeton incorrect", 403)
                role = "admin"
                c.execute("UPDATE auth_bootstrap SET consumed_at=now()")
            elif (
                not actor
                and not c.execute(
                    "SELECT 1 FROM app_users WHERE role='admin' AND deleted_at IS NULL"
                ).fetchone()
            ):
                raise ReviewError("Initialiser d'abord le compte administrateur", 409)
            row = c.execute(
                f"""INSERT INTO app_users(id,email,display_name,password_hash,role)
              VALUES(%s,%s,%s,%s,%s) RETURNING {PUBLIC_FIELDS}""",
                (str(uuid4()), email, name, encoded, role),
            ).fetchone()
            audit(c, "account_created", actor, row["id"])
    except UniqueViolation:
        raise ReviewError("Cette adresse ne peut pas être utilisée", 409) from None
    if setup_token is not None:
        bootstrap_file().unlink(missing_ok=True)
    return row


def login(email: str, password: str) -> dict[str, Any]:
    with transaction() as c:
        row = c.execute(
            "SELECT * FROM app_users WHERE email=%s AND deleted_at IS NULL",
            (email.strip().lower(),),
        ).fetchone()
    # Same costly operation for unknown addresses to reduce account enumeration.
    encoded = row["password_hash"] if row else "scrypt$" + "00" * 16 + "$" + "00" * 64
    if not verify_password(password, encoded):
        raise ReviewError("Adresse ou mot de passe incorrect", 401)
    return {**{key: row[key] for key in PUBLIC_FIELDS.split(",")}, "_verified_hash": encoded}


def new_session(user_id: str | UUID, expected_hash: str | None = None) -> str:
    token = secrets.token_urlsafe(32)
    with transaction() as c:
        # Recheck after a concurrent deletion/password change.
        row = c.execute(
            "SELECT id,password_hash FROM app_users WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
            (user_id,),
        ).fetchone()
        if not row:
            raise ReviewError("Compte indisponible", 401)
        if expected_hash and not hmac.compare_digest(expected_hash, row["password_hash"]):
            raise ReviewError("Identifiants modifiés ; reconnectez-vous", 401)
        c.execute("DELETE FROM auth_sessions WHERE expires_at<now()")
        c.execute(
            """INSERT INTO auth_sessions(token_hash,user_id,expires_at)
          VALUES(%s,%s,%s)""",
            (digest(token), user_id, datetime.now(UTC) + timedelta(hours=12)),
        )
    return token


def session_user(token: str | None) -> dict[str, Any]:
    if not token or len(token) > 128:
        raise ReviewError("Connexion requise", 401)
    with transaction() as c:
        row = c.execute(
            f"""SELECT {",".join("u." + k for k in PUBLIC_FIELDS.split(","))}
          FROM auth_sessions s JOIN app_users u ON u.id=s.user_id
          WHERE s.token_hash=%s AND s.expires_at>now()
          AND s.last_seen_at>now()-interval '2 hours' AND u.deleted_at IS NULL""",
            (digest(token),),
        ).fetchone()
        if not row:
            raise ReviewError("Session expirée ; reconnectez-vous", 401)
        c.execute(
            "UPDATE auth_sessions SET last_seen_at=now() WHERE token_hash=%s", (digest(token),)
        )
    row["id"] = str(row["id"])
    return row


def csrf(token: str) -> str:
    return hashlib.sha256(("biosentinelle-csrf:" + token).encode()).hexdigest()


def check_password(
    user_id: str | UUID, password: str, connection: Connection | None = None
) -> None:
    if connection is None:
        with transaction() as c:
            return check_password(user_id, password, c)
    row = connection.execute(
        "SELECT password_hash FROM app_users WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
        (user_id,),
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise ReviewError("Mot de passe actuel incorrect", 403)


def protect_last_admin(c: Connection, target: str | UUID) -> dict[str, Any]:
    c.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
    row = c.execute(
        "SELECT * FROM app_users WHERE id=%s AND deleted_at IS NULL FOR UPDATE", (target,)
    ).fetchone()
    if not row:
        raise ReviewError("Compte introuvable", 404)
    if (
        row["role"] == "admin"
        and c.execute(
            "SELECT count(*) AS n FROM app_users WHERE role='admin' AND deleted_at IS NULL"
        ).fetchone()["n"]
        <= 1
    ):
        raise ReviewError("Le dernier administrateur ne peut pas être supprimé ou rétrogradé", 409)
    return row


def delete_account(user_id: str | UUID, actor: str | UUID, password: str | None = None) -> str:
    reference = str(uuid4())
    with transaction() as c:
        protect_last_admin(c, user_id)
        if password is not None:
            check_password(user_id, password, c)
        c.execute(
            """UPDATE app_users SET deleted_at=now(),updated_at=now(),email=NULL,
          display_name='Compte supprimé',password_hash=NULL WHERE id=%s""",
            (user_id,),
        )
        c.execute("DELETE FROM auth_sessions WHERE user_id=%s", (user_id,))
        c.execute("DELETE FROM auth_password_resets WHERE user_id=%s", (user_id,))
        c.execute(
            "UPDATE console_tasks SET cancel_requested=true WHERE actor=%s AND status "
            "IN ('queued','running')",
            (str(user_id),),
        )
        c.execute(
            """UPDATE document_tasks SET status='error',error='Compte supprimé',finished_at=now()
          WHERE actor=%s AND status='queued'""",
            (str(user_id),),
        )
        c.execute(
            """UPDATE parcel_dossiers SET status='error',error='Compte supprimé'
          WHERE actor=%s AND status='waiting_analysis'""",
            (str(user_id),),
        )
        c.execute(
            "INSERT INTO auth_erasure_requests(id,user_id) VALUES(%s,%s)", (reference, user_id)
        )
        audit(c, "account_deleted_erasure_requested", actor, user_id)
    return reference
