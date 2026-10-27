"""Resolve snapshot citations for display; the source audit keeps its original IDs."""

import re
from html import escape
from urllib.parse import quote, urlsplit

REFERENCE = re.compile(r"\[?\b(D\d+)\b\]?")


def external_url(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme in ("http", "https")
            and parsed.hostname
            and not re.search(r"[\x00-\x20]", value)
        ):
            return value
    except ValueError:
        pass
    return None


def article_url(source):
    doi = re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
        "",
        (source.get("doi") or "").strip(),
        flags=re.I,
    ).strip()
    if re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        return "https://doi.org/" + quote(doi, safe="/")
    findings = source.get("findings", [])
    for candidate in [source.get("source_url"), *(f.get("source_url") for f in findings)]:
        if url := external_url(candidate):
            return url
    original = source.get("original_url") or ""
    if original.startswith("/documents/"):
        return "/api" + original
    if original.startswith("/api/documents/"):
        return original
    asset = next((f["asset_id"] for f in findings if f.get("asset_id")), None)
    if source.get("id") and asset:
        document_id = quote(str(source["id"]), safe="")
        return f"/api/documents/{document_id}/assets/{quote(str(asset), safe='')}?inline=true"
    return external_url(original)


def source_index(report):
    return {
        d["citation"]: {"title": d["title"], "url": article_url(d)}
        for d in report.get("ledger", [])
    }


def reference_label(identifier, sources, format="html"):
    source = sources.get(identifier)
    if not source:
        label = f"[{identifier}]"
        return escape(label) if format == "html" else label
    title, url = source["title"], source["url"]
    if format == "html":
        if not url:
            return escape(title)
        return (
            f'<a class="source-link" href="{escape(url, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" title="{escape(title, quote=True)}">'
            f"{escape(title)}</a>"
        )
    if format == "markdown":
        label = re.sub(r"([\\\[\]])", r"\\\1", escape(title, quote=False))
        safe_url = url.replace("<", "%3C").replace(">", "%3E") if url else None
        return f"[{label}](<{safe_url}>)" if safe_url else label
    return f"{title} ({url})" if url else title


def link_text(text, sources, format="html"):
    parts, start = [], 0
    for match in REFERENCE.finditer(text):
        before = text[start : match.start()]
        parts.extend(
            [
                escape(before) if format == "html" else before,
                reference_label(match[1], sources, format),
            ]
        )
        start = match.end()
    tail = text[start:]
    parts.append(escape(tail) if format == "html" else tail)
    return "".join(parts)


def remaining_references(identifiers, text, sources, format="html"):
    mentioned = {m[1] for m in REFERENCE.finditer(text) if m[1] in sources}
    return " · ".join(
        reference_label(c, sources, format)
        for c in dict.fromkeys(identifiers)
        if c not in mentioned
    )
