"""Consultation ponctuelle de l'inventaire DREAL Normandie via WFS 2.0."""

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

BASE = "https://ogc.geo-ide.developpement-durable.gouv.fr/wxs"
MAP = "/opt/data/stack/mapfiles/1.4/org_4930752/be433f7d-cb7a-426a-92c5-491a6a155a62.internet.map"
LAYER = "drealnorm_zh_s_r28"
WFS = "{http://www.opengis.net/wfs/2.0}"
GML = "{http://www.opengis.net/gml/3.2}"
MS = "{http://mapserver.gis.umn.edu/mapserver}"
PAGE_SIZE = 100
MAX_PAGES = 20
MAX_BYTES = 8 * 1024 * 1024


def _ring(ring, lon, lat):
    pos = ring.find(f"{GML}LinearRing/{GML}posList")
    if pos is None or not pos.text or pos.get("srsDimension", "2") != "2":
        raise ValueError("Anneau GML invalide")
    nums = [float(v) for v in pos.text.split()]
    if len(nums) < 8 or len(nums) % 2 or not all(math.isfinite(v) for v in nums):
        raise ValueError("Coordonnées GML invalides")
    # WFS 2.0 EPSG:4326 uses latitude, longitude axis order.
    points = [(nums[i + 1], nums[i]) for i in range(0, len(nums), 2)]
    if points[0] != points[-1]:
        raise ValueError("Anneau non fermé")
    inside = False
    for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False):
        cross = (lon - x1) * (y2 - y1) - (lat - y1) * (x2 - x1)
        if (
            abs(cross) < 1e-14
            and min(x1, x2) <= lon <= max(x1, x2)
            and min(y1, y2) <= lat <= max(y1, y2)
        ):
            return 2
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return int(inside)


def _contains(geometry, lon, lat):
    surface = geometry.find(f"{GML}MultiSurface")
    if surface is None or surface.get("srsName") != "urn:ogc:def:crs:EPSG::4326":
        raise ValueError("Géométrie ou projection GML inattendue")
    members = surface.findall(f"{GML}surfaceMember")
    if not members:
        raise ValueError("MultiSurface vide")
    matches = False
    for member in members:
        poly = member.find(f"{GML}Polygon")
        if poly is None:
            raise ValueError("Polygone GML attendu")
        exterior = poly.find(f"{GML}exterior")
        if exterior is None:
            raise ValueError("Contour extérieur absent")
        outer = _ring(exterior, lon, lat)
        holes = [_ring(hole, lon, lat) for hole in poly.findall(f"{GML}interior")]
        # A hole boundary belongs to the polygon boundary.
        matches |= outer == 2 or (outer == 1 and (2 in holes or not any(holes)))
    return matches


def _page(raw, lon, lat):
    root = ET.fromstring(raw)
    if root.tag != WFS + "FeatureCollection":
        raise ValueError("FeatureCollection WFS attendue")
    returned = root.get("numberReturned")
    matched = root.get("numberMatched")
    if (
        not returned
        or not returned.isdigit()
        or not matched
        or not (matched.isdigit() or matched == "unknown")
    ):
        raise ValueError("Comptages WFS absents ou invalides")
    members = root.findall(WFS + "member")
    if len(members) != int(returned):
        raise ValueError("Réponse WFS incomplète")
    found = []
    ids = []
    for member in members:
        feature = member.find(MS + LAYER)
        if feature is None:
            raise ValueError("Objet WFS invalide")
        geom = feature.find(MS + "geometry")
        identifier = feature.findtext(MS + "pk_zh")
        if geom is None or not identifier or not identifier.isdigit():
            raise ValueError("Identifiant ou géométrie absent")
        ids.append(identifier)
        properties = {
            node.tag[len(MS) :]: node.text
            for node in feature
            if node.tag.startswith(MS) and node.tag != MS + "geometry"
        }
        if _contains(geom, lon, lat):
            found.append({"source_id": identifier, "properties": properties})
    return found, ids, len(members), matched, bool(root.get("next"))


def collect(location: dict, transport=None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "status": "unavailable",
        "nature": "inventoried",
        "features": [],
        "source_url": BASE,
        "projection": "EPSG:4326",
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
    pages: list[str] = []
    try:
        lon, lat = float(location["longitude"]), float(location["latitude"])
        if (
            not math.isfinite(lon)
            or not math.isfinite(lat)
            or not (-180 <= lon <= 180 and -90 <= lat <= 90)
        ):
            raise ValueError("Coordonnées invalides")
        params = {
            "map": MAP,
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": LAYER,
            "COUNT": str(PAGE_SIZE),
            "SRSNAME": "EPSG:4326",
            "SORTBY": "pk_zh",
            "BBOX": (f"{lat - 0.0001:.7f},{lon - 0.0001:.7f},"
                     f"{lat + 0.0001:.7f},{lon + 0.0001:.7f},urn:ogc:def:crs:EPSG::4326"),
        }
        record["parameters"] = params.copy()
        features = []
        total = 0
        archived_bytes = 0
        all_ids = set()
        expected = None
        with httpx.Client(
            timeout=15, follow_redirects=False, trust_env=False, transport=transport
        ) as client:
            for _ in range(MAX_PAGES):
                with client.stream(
                    "GET", BASE, params={**params, "STARTINDEX": str(total)}
                ) as response:
                    record["http_status"] = response.status_code
                    response.raise_for_status()
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if archived_bytes + len(data) > MAX_BYTES:
                            raise ValueError("Réponse WFS trop volumineuse")
                raw = bytes(data)
                archived_bytes += len(raw)
                pages.append(raw.decode("utf-8"))
                found, ids, count, matched, next_page = _page(raw, lon, lat)
                if len(set(ids)) != len(ids) or all_ids.intersection(ids):
                    raise ValueError("Objets dupliqués pendant la pagination")
                all_ids.update(ids)
                features.extend(found)
                total += count
                if matched != "unknown":
                    if expected is not None and expected != int(matched):
                        raise ValueError("Total WFS modifié pendant la pagination")
                    expected = int(matched)
                if count > PAGE_SIZE or (expected is not None and total > expected):
                    raise ValueError("Pagination WFS incohérente")
                if not next_page and expected is not None and total == expected:
                    break
                if not next_page and expected is None:
                    raise ValueError("Total WFS inconnu : exhaustivité non vérifiable")
                if not count or (expected is not None and total == expected and next_page):
                    raise ValueError("Pagination WFS incomplète")
            else:
                raise ValueError("Limite de pagination WFS atteinte")
        ids = [f["source_id"] for f in features]
        if len(ids) != len(set(ids)):
            raise ValueError("Objets dupliqués pendant la pagination")
        record.update(status="success" if features else "empty", features=features)
    except httpx.RequestError as exc:
        record.update(status="unavailable", error=f"{type(exc).__name__}: accès DREAL indisponible")
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        record.update(
            status="unavailable" if code in (429, 502, 503, 504) else "error", error=f"HTTP {code}"
        )
    except (ValueError, KeyError, TypeError, UnicodeError, ParseError, DefusedXmlException) as exc:
        record.update(status="error", error=str(exc)[:500])
    if pages:
        archive = json.dumps(pages, ensure_ascii=False, separators=(",", ":"))
        record.update(
            raw_response=archive, sha256=hashlib.sha256(archive.encode("utf-8")).hexdigest()
        )
    return record
