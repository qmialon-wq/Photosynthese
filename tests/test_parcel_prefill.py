import asyncio
import json

import httpx
import pytest

from workers.documents import parcel_prefill as prefill


def collection(properties, geometry=None):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry,
            }
        ],
    }


def run(handler):
    return asyncio.run(
        prefill.collect_async({"latitude": 49.18, "longitude": -0.37}, httpx.MockTransport(handler))
    )


def test_prefill_records_sources_and_never_invents_a_project():
    def handler(request):
        if request.url.host == "geo.api.gouv.fr":
            assert request.url.params["lat"] == "49.18"
            return httpx.Response(200, json=[{"nom": "Caen", "code": "14118"}])
        assert json.loads(request.url.params["geom"])["coordinates"] == [-0.37, 49.18]
        if "rpg" in request.url.path:
            assert request.url.params["annee"] == "2024"
            return httpx.Response(200, json=collection({"code_group": "18"}))
        return httpx.Response(200, json=collection({"contenance": 1400}))

    result = run(handler)
    assert result["values"] == {"locality": "Caen", "area_m2": 1400, "land_type": "pasture"}
    assert "project_type" not in result["values"]
    assert all(source["retrieved_at"] for source in result["sources"].values())


def test_partial_failure_and_ambiguous_parcels_still_allow_manual_entry():
    def handler(request):
        if request.url.host == "geo.api.gouv.fr":
            return httpx.Response(200, json=[{"nom": "Caen"}])
        if "rpg" in request.url.path:
            return httpx.Response(503)
        response = collection({"contenance": 1400})
        response["features"] *= 2
        return httpx.Response(200, json=response)

    result = run(handler)
    assert result["values"] == {"locality": "Caen"}
    assert result["sources"]["cadastre"]["status"] == "ambiguous"
    assert result["sources"]["rpg"]["status"] == "unavailable"


def test_unavailable_services_return_no_guessed_values():
    result = run(lambda request: httpx.Response(503))
    assert result["values"] == {}


def test_cadastral_geometry_estimate_subtracts_holes():
    outer = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]
    hole = [[0, 0], [0.0005, 0], [0.0005, 0.0005], [0, 0.0005], [0, 0]]
    area = prefill.geometry_area({"type": "Polygon", "coordinates": [outer]})
    assert area == pytest.approx(12364, rel=0.001)
    with_hole = prefill.geometry_area({"type": "Polygon", "coordinates": [outer, hole]})
    assert with_hole == pytest.approx(area * 0.75, rel=0.001)
    assert prefill.geometry_area({"type": "Point", "coordinates": [0, 0]}) is None


def test_truncated_or_oversized_reply_is_not_a_success():
    def truncated(request):
        if request.url.host == "geo.api.gouv.fr":
            return httpx.Response(200, json=[])
        data = collection({"contenance": 1000})
        data["numberMatched"] = 3
        return httpx.Response(200, json=data)

    assert run(truncated)["values"] == {}
    result = run(lambda request: httpx.Response(200, content=b"x" * (prefill.MAX_BYTES + 1)))
    assert result["values"] == {}
