import asyncio
import json

import httpx
import pytest

from workers.documents import ign


def run(handler, completed=None):
    return asyncio.run(
        ign.collect_async(
            {"longitude": -0.37, "latitude": 49.18},
            completed,
            transport=httpx.MockTransport(handler),
        )
    )


def test_empty_and_coordinate_order():
    def handler(request):
        assert request.url.scheme == "https" and request.url.host == "apicarto.ign.fr"
        assert json.loads(request.url.params["geom"]) == {
            "type": "Point",
            "coordinates": [-0.37, 49.18],
        }
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    layers = run(handler)
    assert all(r["status"] == "empty" and r["sha256"] for r in layers.values())
    assert ign.status(layers) == "complete"


def test_errors_are_never_empty_and_retries_are_bounded():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if "znieff1" in request.url.path:
            return httpx.Response(200, content=b"{truncated")
        if "znieff2" in request.url.path:
            return httpx.Response(503)
        if "natura-habitat" in request.url.path:
            raise httpx.ConnectError("offline")
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    layers = run(handler)
    assert ign.status(layers) == "failed"
    assert [r["status"] for r in layers.values()] == [
        "error",
        "unavailable",
        "unavailable",
        "error",
    ]
    assert len(calls) == 6
    assert not any("127.0.0.1" in c for c in calls)


def test_partial_resume_size_and_truncation(monkeypatch):
    complete = {"znieff1": {"status": "empty"}}
    monkeypatch.setattr(ign, "MAX_BYTES", 80)
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, content=b"x" * 81)

    layers = run(handler, complete)
    assert len(calls) == 3 and ign.status(layers) == "partial"
    assert layers["znieff2"]["status"] == "error"
    with pytest.raises(ValueError, match="tronquée"):
        ign.normalize(
            json.dumps({"type": "FeatureCollection", "features": [], "totalFeatures": 1}).encode(),
            "znieff1",
            "url",
            "date",
        )


def test_real_shaped_feature_normalized():
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "test",
                "properties": {"id_mnhn": "test-id", "nom": "Fixture de test"},
                "geometry": None,
            }
        ],
    }
    layers = run(lambda _: httpx.Response(200, json=data))
    assert all(r["status"] == "success" for r in layers.values())
    assert layers["znieff1"]["features"][0]["source_id"] == "test-id"
