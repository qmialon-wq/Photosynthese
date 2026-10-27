"""Legacy feature tests use an explicit test principal; auth tests exercise the real guard."""

import pytest
from fastapi import Request


@pytest.fixture(autouse=True)
def legacy_test_principal(request, monkeypatch):
    if request.node.path.name == "test_authentication.py":
        yield
        return
    from app.main import app
    from app.security import authorize_request

    from shared import accounts

    async def test_identity(http_request: Request):
        http_request.state.user = {
            "id": http_request.headers.get("X-Reviewer", "local"),
            "role": "admin",
        }
        yield

    # No production fallback: this override exists only inside pytest.
    monkeypatch.setattr(accounts, "ensure_bootstrap", lambda: None)
    app.dependency_overrides[authorize_request] = test_identity
    yield
    app.dependency_overrides.pop(authorize_request, None)
