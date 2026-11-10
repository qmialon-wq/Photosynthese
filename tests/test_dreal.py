import hashlib
import json

import httpx

from workers.documents import dreal

POINT = {"latitude": 49.7, "longitude": -1.368}


def response(features="", count=0, matched="0", next_attr=""):
    return f'''<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:gml="http://www.opengis.net/gml/3.2"
 xmlns:ms="http://mapserver.gis.umn.edu/mapserver"
 numberReturned="{count}" numberMatched="{matched}" {next_attr}>{features}
</wfs:FeatureCollection>'''


def feature(identifier="1", hole=""):
    return f"""<wfs:member><ms:drealnorm_zh_s_r28><ms:geometry>
<gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326">
<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>
<gml:posList>49 -2 49 -1 50 -1 50 -2 49 -2</gml:posList></gml:LinearRing></gml:exterior>
{hole}</gml:Polygon></gml:surfaceMember></gml:MultiSurface></ms:geometry>
<ms:pk_zh>{identifier}</ms:pk_zh><ms:qualite>fiable</ms:qualite></ms:drealnorm_zh_s_r28></wfs:member>"""


def run(handler):
    return dreal.collect(POINT, transport=httpx.MockTransport(handler))


def test_success_and_archived_hash():
    result = run(lambda request: httpx.Response(200, text=response(feature(), 1, "1")))
    assert result["status"] == "success"
    assert result["features"][0]["source_id"] == "1"
    assert hashlib.sha256(result["raw_response"].encode()).hexdigest() == result["sha256"]
    assert len(json.loads(result["raw_response"])) == 1
    assert result["parameters"]["BBOX"].startswith("49.6999000,-1.3681000")


def test_hole_and_empty():
    hole = ("<gml:interior><gml:LinearRing><gml:posList>49.6 -1.5 49.6 -1.2 "
            "49.8 -1.2 49.8 -1.5 49.6 -1.5</gml:posList></gml:LinearRing></gml:interior>")
    assert (
        run(lambda request: httpx.Response(200, text=response(feature(hole=hole), 1, "1")))[
            "status"
        ]
        == "empty"
    )
    assert run(lambda request: httpx.Response(200, text=response()))["status"] == "empty"


def test_invalid_and_incomplete_never_empty():
    for body in (
        "",
        "<broken",
        response(count=1, matched="1"),
        response(count=0, matched="2"),
        response(count=0, matched="unknown"),
        response(feature().replace("EPSG::4326", "EPSG::2154"), 1, "1"),
    ):
        assert run(lambda request, body=body: httpx.Response(200, text=body))["status"] == "error"


def test_pagination(monkeypatch):
    monkeypatch.setattr(dreal, "PAGE_SIZE", 1)

    def handler(request):
        index = request.url.params["STARTINDEX"]
        return httpx.Response(
            200,
            text=response(
                feature("1" if index == "0" else "2"), 1, "2", 'next="next"' if index == "0" else ""
            ),
        )

    result = run(handler)
    assert result["status"] == "success"
    assert len(result["features"]) == 2
    assert len(json.loads(result["raw_response"])) == 2


def test_unavailable():
    def fail(request):
        raise httpx.ConnectError("offline", request=request)

    assert run(fail)["status"] == "unavailable"
    assert run(lambda request: httpx.Response(503))["status"] == "unavailable"
