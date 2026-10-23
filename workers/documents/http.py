"""HTTP borné, cache local et contrôle des destinations, sans contournement d'accès."""

import hashlib
import ipaddress
import json
import random
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import httpx

from shared.documents.config import DocumentSettings

from .storage import DocumentStorage


class FetchError(Exception):
    pass


def public_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 80, 443)
    ):
        raise FetchError("URL documentaire non autorisée")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise FetchError("Résolution DNS impossible") from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise FetchError("Destination privée, locale ou réservée refusée")


def retry_after(value: str | None) -> float:
    if not value:
        return 0
    try:
        return max(0, float(value))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0


class SafeHTTP:
    def __init__(
        self,
        settings: DocumentSettings,
        *,
        client: httpx.Client | None = None,
        validate: Callable[[str], None] = public_url,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[..., None] = lambda **_: None,
    ) -> None:
        self.settings, self.validate, self.sleep, self.log = settings, validate, sleep, log
        self.storage = DocumentStorage(settings.root)
        self.client = client or httpx.Client(
            timeout=settings.timeout_seconds, follow_redirects=False, trust_env=False
        )
        self.next_request: dict[str, float] = {}

    def close(self) -> None:
        self.client.close()

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache: bool = True,
        max_bytes: int | None = None,
    ) -> tuple[bytes, dict[str, str], str]:
        if params:
            parsed = urlsplit(url)
            query = "&".join(filter(None, [parsed.query, urlencode(params)]))
            url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
        digest = hashlib.sha256(url.encode()).hexdigest()
        metadata = self.storage.path(f"cache/http/{digest}.json")
        content = self.storage.path(f"cache/http/{digest}.body")
        limit = max_bytes or self.settings.max_file_bytes
        if cache and metadata.is_file() and content.is_file():
            try:
                entry = json.loads(metadata.read_text(encoding="utf-8"))
                data = content.read_bytes()
                if (
                    time.time() - entry["time"] < self.settings.cache_ttl_seconds
                    and len(data) <= limit
                    and hashlib.sha256(data).hexdigest() == entry["sha256"]
                ):
                    self.log(
                        stage="http",
                        message="Réponse du cache",
                        data={"host": urlsplit(url).hostname},
                    )
                    return data, entry["headers"], entry["url"]
            except (OSError, ValueError, KeyError):
                pass
        current = url
        for redirect in range(6):
            self.validate(current)
            host = urlsplit(current).hostname or ""
            for attempt in range(self.settings.retries + 1):
                gate = self.storage.path(
                    f"cache/limits/{hashlib.sha256(host.encode()).hexdigest()}.json"
                )
                not_before = self.next_request.get(host, 0)
                if gate.is_file():
                    try:
                        not_before = max(not_before, json.loads(gate.read_text())["not_before"])
                    except (OSError, ValueError, KeyError):
                        pass
                delay = max(0, not_before - time.time())
                if delay > 60:
                    raise FetchError(
                        "Quota distant : reprise différée, consulter les événements HTTP"
                    )
                self.sleep(delay)
                headers = {
                    "User-Agent": "BioSentinelle/0.1"
                    + (
                        f" (mailto:{self.settings.contact_email})"
                        if self.settings.contact_email
                        else ""
                    )
                }
                if host == "api.openalex.org" and self.settings.openalex_api_key:
                    headers["Authorization"] = (
                        "Bearer " + self.settings.openalex_api_key.get_secret_value()
                    )
                self.next_request[host] = time.time() + self.settings.request_interval
                try:
                    with self.client.stream("GET", current, headers=headers) as response:
                        self.log(
                            stage="http",
                            message="Appel distant",
                            data={
                                "host": host,
                                "status": response.status_code,
                                "attempt": attempt + 1,
                            },
                        )
                        advertised = response.headers.get("x-rate-limit-limit")
                        interval = response.headers.get("x-rate-limit-interval", "1s").rstrip("s")
                        if advertised:
                            try:
                                self.next_request[host] = max(
                                    self.next_request[host],
                                    time.time() + float(interval) / max(1, float(advertised)),
                                )
                            except ValueError:
                                pass
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("location")
                            if not location or redirect == 5:
                                raise FetchError("Redirection documentaire invalide")
                            current = urljoin(current, location)
                            break
                        if response.status_code in (408, 429, 500, 502, 503, 504):
                            wait = max(
                                retry_after(response.headers.get("retry-after")),
                                2**attempt + random.random() / 4,
                            )
                            self.next_request[host] = time.time() + wait
                            self.storage.json(
                                str(gate.relative_to(self.storage.root)),
                                {"not_before": self.next_request[host]},
                            )
                            if attempt == self.settings.retries or wait > 60:
                                raise FetchError(
                                    f"API indisponible ou limitée (HTTP {response.status_code})"
                                )
                            continue
                        if response.status_code != 200:
                            raise FetchError(
                                f"Accès refusé ou indisponible (HTTP {response.status_code})"
                            )
                        length = response.headers.get("content-length", "")
                        if length.isdigit() and int(length) > limit:
                            raise FetchError("Réponse trop volumineuse")
                        parts, size = [], 0
                        for part in response.iter_bytes(65536):
                            size += len(part)
                            if size > limit:
                                raise FetchError("Réponse trop volumineuse")
                            parts.append(part)
                        data = b"".join(parts)
                        kept_headers = {"content-type": response.headers.get("content-type", "")}
                        if cache:
                            self.storage.write(f"cache/http/{digest}.body", data)
                            self.storage.json(
                                f"cache/http/{digest}.json",
                                {
                                    "time": time.time(),
                                    "sha256": hashlib.sha256(data).hexdigest(),
                                    "headers": kept_headers,
                                    "url": current,
                                },
                            )
                        return data, kept_headers, current
                except (httpx.HTTPError, OSError) as exc:
                    self.log(
                        stage="http",
                        message="Erreur réseau",
                        data={"host": host, "attempt": attempt + 1},
                    )
                    if attempt == self.settings.retries:
                        raise FetchError("Échec réseau après retries") from exc
                    self.sleep(2**attempt)
            else:
                raise FetchError("Échec HTTP")
        raise FetchError("Trop de redirections")

    def json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        data, _, _ = self.get(url, params=params, max_bytes=8 * 1024 * 1024)
        try:
            parsed = json.loads(data)
        except ValueError as exc:
            raise FetchError("Réponse API non JSON") from exc
        if not isinstance(parsed, dict):
            raise FetchError("Réponse API de format inattendu")
        return parsed
