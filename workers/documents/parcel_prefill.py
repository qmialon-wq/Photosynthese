"""Optional, bounded suggestions from public data; never replace user declarations."""

import asyncio
import json
import math
from datetime import UTC, datetime

import httpx

COMMUNES = "https://geo.api.gouv.fr/communes"
CADASTRE = "https://apicarto.ign.fr/api/cadastre/parcelle"
RPG = "https://apicarto.ign.fr/api/rpg/v2"
MAX_BYTES = 2 * 1024 * 1024
RPG_YEAR = 2024


def geometry_area(geometry: dict) -> float | None:
    """Spherical GeoJSON area in m², with holes; a suggestion, never a legal surface."""
    try:
        if geometry.get("type") not in ("Polygon", "MultiPolygon"):
            return None
        polygons = geometry["coordinates"]
        if geometry["type"] == "Polygon":
            polygons = [polygons]
        total = 0.0
        for polygon in polygons:
            parts = []
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    return None
                points = []
                for point in ring:
                    lon, lat = point[:2]
                    if not all(
                        isinstance(n, int | float) and not isinstance(n, bool) and math.isfinite(n)
                        for n in (lon, lat)
                    ):
                        return None
                    if abs(lon) > 180 or abs(lat) > 90:
                        return None
                    points.append((math.radians(lon), math.radians(lat)))
                surface = 0.0
                for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False):
                    dx = (x2 - x1 + math.pi) % (2 * math.pi) - math.pi
                    surface += dx * (2 + math.sin(y1) + math.sin(y2))
                parts.append(abs(surface) * 6_371_008.8**2 / 2)
            if not parts or sum(parts[1:]) > parts[0]:
                return None
            total += parts[0] - sum(parts[1:])
        return round(total, 1) if 0 < total <= 1_000_000_000 else None
    except (KeyError, ValueError, TypeError, IndexError):
        return None


async def fetch(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    record = {
        "source_url": url,
        "status": "unavailable",
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
    try:
        async with asyncio.timeout(12):
            async with client.stream("GET", url, params=params) as response:
                response.raise_for_status()
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_BYTES:
                        raise ValueError("Réponse trop volumineuse")
                data = json.loads(raw, parse_constant=lambda _: None)
        if url == COMMUNES:
            rows = data
        else:
            if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
                raise ValueError("FeatureCollection attendue")
            rows = data.get("features")
            total = data.get("totalFeatures", data.get("numberMatched"))
            if isinstance(total, int) and total != len(rows or []):
                raise ValueError("Réponse incomplète")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Réponse invalide")
        # A point on a boundary may match several parcels: never pick one at random.
        record.update(status="success" if len(rows) == 1 else "empty" if not rows else "ambiguous")
        record["properties"] = (
            rows[0]
            if url == COMMUNES and len(rows) == 1
            else (rows[0].get("properties", {}) if len(rows) == 1 else {})
        )
        if not isinstance(record["properties"], dict):
            raise ValueError("Propriétés invalides")
        if url == CADASTRE and len(rows) == 1:
            record["estimated_area_m2"] = geometry_area(rows[0].get("geometry") or {})
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError, UnicodeError):
        record.update(status="unavailable", properties={})
    return record


async def collect_async(location: dict, transport=None) -> dict:
    geom = json.dumps(
        {"type": "Point", "coordinates": [location["longitude"], location["latitude"]]}
    )
    async with httpx.AsyncClient(
        timeout=10, follow_redirects=False, trust_env=False, transport=transport
    ) as client:
        commune, parcel, farming = await asyncio.gather(
            fetch(
                client,
                COMMUNES,
                {"lat": location["latitude"], "lon": location["longitude"], "fields": "nom,code"},
            ),
            fetch(client, CADASTRE, {"geom": geom, "_limit": 3}),
            fetch(client, RPG, {"geom": geom, "_limit": 3, "annee": RPG_YEAR}),
        )
    values = {}
    name = commune["properties"].get("nom")
    if commune["status"] == "success" and isinstance(name, str) and name.strip():
        values["locality"] = name.strip()[:200]
    area = parcel["properties"].get("contenance", parcel.get("estimated_area_m2"))
    if (
        parcel["status"] == "success"
        and isinstance(area, int | float)
        and not isinstance(area, bool)
        and math.isfinite(area)
        and 0 < area <= 1_000_000_000
    ):
        values["area_m2"] = area
        parcel["area_method"] = (
            "contenance" if "contenance" in parcel["properties"] else "cartographic_estimate"
        )
    props = farming["properties"]
    farming["year"] = RPG_YEAR
    group = str(props.get("code_groupe", props.get("code_group", "")))
    if farming["status"] == "success" and group in ("18", "19"):
        values["land_type"] = "pasture"
    return {
        "values": values,
        "sources": {"commune": commune, "cadastre": parcel, "rpg": farming},
        "retrieved_at": datetime.now(UTC).isoformat(),
        "notice": "Suggestions à vérifier : surface cadastrale ou estimation cartographique, "
        f"prairie déclarée au RPG {RPG_YEAR} (à confirmer sur le terrain). "
        "Le projet envisagé reste votre choix. Un point ne décrit pas toute la parcelle.",
    }


def collect(location: dict) -> dict:
    return asyncio.run(collect_async(location))
