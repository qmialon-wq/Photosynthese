"""HTTPS session and origin checks used by the optional public tunnel, without a DB."""

import pytest
from app.auth import session_response
from app.security import check_origin
from fastapi import Request, Response

from shared import accounts
from shared.review.database import ReviewError

PUBLIC_ORIGIN = "https://petection-example.ngrok-free.dev"


@pytest.mark.parametrize("origin", [PUBLIC_ORIGIN, "http://localhost:8080"])
def test_tunnel_and_local_origins_are_accepted(monkeypatch, origin):
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", f"http://localhost:8080,{PUBLIC_ORIGIN}")
    request = Request({"type": "http", "headers": [(b"origin", origin.encode())]})
    check_origin(request)


@pytest.mark.parametrize(
    "origin",
    ["https://other.ngrok-free.dev", PUBLIC_ORIGIN + ".example.org"],
)
def test_other_public_origins_remain_forbidden(monkeypatch, origin):
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", f"http://localhost:8080,{PUBLIC_ORIGIN}")
    request = Request({"type": "http", "headers": [(b"origin", origin.encode())]})
    with pytest.raises(ReviewError) as error:
        check_origin(request)
    assert error.value.status == 403


def test_https_session_preserves_cookie_and_csrf_protection(monkeypatch):
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setattr(accounts, "new_session", lambda *_: "test-session")
    response = Response()
    result = session_response(response, {"id": "test-user"})
    cookie = response.headers["set-cookie"].lower()
    assert "; secure" in cookie
    assert "; httponly" in cookie
    assert "; samesite=lax" in cookie
    assert result["csrf_token"] == accounts.csrf("test-session")
