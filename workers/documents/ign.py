"""Bounded IGN Nature connector. Only the four fixed HTTPS endpoints are reachable."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import httpx

LAYERS = ("znieff1", "znieff2", "natura-habitat", "natura-oiseaux")
BASE = "https://apicarto.ign.fr/api/nature/"
MAX_BYTES = 8 * 1024 * 1024


def normalize(raw: bytes, layer: str, url: str, retrieved_at: str) -> list[dict[str, Any]]:
    data = json.loads(
        raw,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"Nombre JSON invalide : {value}")
        ),
    )
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("FeatureCollection GeoJSON attendue")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("Liste features absente")
    if (
        len(features) >= 1000
        or any(
            isinstance(data.get(key), int) and data[key] != len(features)
            for key in ("totalFeatures", "numberMatched")
        )
        or any(
            link.get("rel") == "next" for link in data.get("links", []) if isinstance(link, dict)
        )
    ):
        raise ValueError("Réponse potentiellement tronquée ; consultation incomplète")
    result = []
    for f in features:
        if (
            not isinstance(f, dict)
            or f.get("type") != "Feature"
            or not isinstance(f.get("properties"), dict)
        ):
            raise ValueError("Objet GeoJSON invalide")
        props = f["properties"]
        identifier = props.get("id_mnhn") or props.get("sitecode") or f.get("id")
        name = props.get("nom") or props.get("sitename") or props.get("nom_site")
        if not identifier or not isinstance(name, str) or not name.strip():
            raise ValueError("Identifiant ou nom du zonage absent")
        geometry = f.get("geometry")
        if geometry is not None and (
            not isinstance(geometry, dict)
            or geometry.get("type") not in ("Polygon", "MultiPolygon")
            or not isinstance(geometry.get("coordinates"), list)
        ):
            raise ValueError("Géométrie de zonage invalide")
        result.append(
            {
                "layer": layer,
                "source_id": str(identifier),
                "name": name,
                "properties": props,
                "geometry": geometry,
                "source_url": url,
                "retrieved_at": retrieved_at,
            }
        )
    return result


async def query_layer(client: httpx.AsyncClient, layer: str, point: dict) -> dict:
    if layer not in LAYERS:
        raise ValueError("Couche IGN non autorisée")
    url = BASE + layer
    record: dict[str, Any] = {
        "layer": layer,
        "source_url": url,
        "features": [],
        "status": "unavailable",
        "attempts": 0,
    }
    for attempt in range(2):
        record.update(attempts=attempt + 1, retrieved_at=datetime.now(UTC).isoformat())
        try:
            async with asyncio.timeout(15):
                async with client.stream(
                    "GET",
                    url,
                    params={
                        "geom": json.dumps(point, separators=(",", ":")),
                        "_limit": 1000,
                    },
                ) as response:
                    record["http_status"] = response.status_code
                    if response.status_code in (429, 502, 503, 504):
                        record.update(status="unavailable", error=f"HTTP {response.status_code}")
                        continue
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_BYTES:
                            raise ValueError("Réponse supérieure à 8 Mio ; non exploitable")
                    raw = bytes(chunks)
                    record.update(
                        raw_response=raw.decode("utf-8"), sha256=hashlib.sha256(raw).hexdigest()
                    )
                    record["features"] = normalize(raw, layer, url, record["retrieved_at"])
                    record["status"] = "success" if record["features"] else "empty"
                    record.pop("error", None)
                    return record
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError) as exc:
            record.update(
                status="unavailable", error=f"{type(exc).__name__}: accès IGN indisponible"
            )
        except (ValueError, UnicodeError, httpx.HTTPError) as exc:
            record.update(status="error", error=str(exc)[:500])
            return record
    return record


async def collect_async(
    location: dict, completed: dict | None = None, persist=None, transport=None
) -> dict:
    point = {"type": "Point", "coordinates": [location["longitude"], location["latitude"]]}
    results = dict(completed or {})
    async with httpx.AsyncClient(
        timeout=15, follow_redirects=False, trust_env=False, transport=transport
    ) as client:
        try:
            async with asyncio.timeout(120):
                for layer in LAYERS:
                    if layer in results:
                        continue  # Resume archived layers after a worker restart.
                    results[layer] = await query_layer(client, layer, point)
                    if persist:
                        persist(results)
        except TimeoutError:
            pass
    for layer in LAYERS:
        if layer not in results:
            results[layer] = {
                "layer": layer,
                "source_url": BASE + layer,
                "status": "unavailable",
                "features": [],
                "attempts": 0,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "error": "Budget global de 120 secondes épuisé",
            }
    return results


def collect(location: dict, completed=None, persist=None) -> dict:
    return asyncio.run(collect_async(location, completed, persist))


def status(layers: dict) -> str:
    ok = sum(row["status"] in ("success", "empty") for row in layers.values())
    return "complete" if ok == 4 else "partial" if ok else "failed"
