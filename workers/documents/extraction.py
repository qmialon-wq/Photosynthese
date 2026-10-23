"""Extraction réelle par page ; aucun OCR ou texte généré n'est simulé."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from shared.documents.config import DocumentSettings

VERSION = "document-text-v1"


def language(text: str) -> str:
    if sum(c.isalpha() for c in text) < 40:
        return "und"
    from langdetect import DetectorFactory, detect_langs
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 42
    try:
        result = detect_langs(text[:10000])[0]
        return result.lang if result.prob >= 0.8 else "und"
    except LangDetectException:
        return "und"


def clean_page(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\x00", "").replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\n(?=[a-zà-ÿ])", "", text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()).strip()


def extract_pages(path: Path, format: str, settings: DocumentSettings) -> dict[str, Any]:
    if path.stat().st_size > settings.max_file_bytes:
        raise ValueError("Document trop volumineux")
    pages: list[dict[str, Any]] = []
    warnings = []
    if format == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("PDF chiffré : mot de passe requis, aucun contournement")
        if len(reader.pages) > settings.max_pdf_pages:
            raise ValueError("PDF avec trop de pages")
        total = 0
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            total += len(text)
            if total > settings.max_text_chars:
                raise ValueError("Texte extrait trop volumineux")
            links = []
            for annotation in (page.get("/Annots") or [])[:1000]:
                try:
                    action = annotation.get_object().get("/A")
                    if action and action.get("/URI"):
                        links.append({"type": "link", "url": str(action["/URI"])[:2000]})
                except (AttributeError, TypeError, ValueError):
                    continue
            pages.append({"page_number": i + 1, "raw_text": text, "references": links})
    elif format == "xml":
        from defusedxml import ElementTree

        root = ElementTree.parse(path).getroot()
        if root.tag.rsplit("}", 1)[-1] != "article":
            raise ValueError("XML non JATS : aucun article exploitable")
        body = root.find(".//body")
        if body is None:
            raise ValueError("Texte intégral XML absent")
        refs = [
            {
                "type": "bibliography",
                "text": " ".join(r.itertext()).strip(),
                "id": r.attrib.get("id"),
            }
            for r in root.findall(".//ref-list/ref")
        ]
        text = "\n".join(t.strip() for t in body.itertext() if t.strip())
        reference_text = "\n".join(r["text"] for r in refs)
        if reference_text:
            text += "\nReferences\n" + reference_text
        pages = [{"page_number": 1, "raw_text": text, "references": refs}]
        warnings.append("XML : unité logique 1, sans pagination PDF")
    elif format in ("txt", "md"):
        pages = [{"page_number": 1, "raw_text": path.read_text(encoding="utf-8"), "references": []}]
        warnings.append("Texte : unité logique 1, sans pagination PDF")
    else:
        raise ValueError("Format documentaire non pris en charge")
    if sum(len(p["raw_text"]) for p in pages) > settings.max_text_chars:
        raise ValueError("Texte extrait trop volumineux")
    reference_section = False
    for page in pages:
        page["clean_text"] = clean_page(page["raw_text"])
        page["language"] = language(page["clean_text"])
        heading = re.search(
            r"(?im)^\s*(?:references|références|bibliographie|bibliography)\s*$", page["clean_text"]
        )
        page["reference_start"] = 0 if reference_section else heading.start() if heading else None
        reference_section = reference_section or heading is not None
        if not page["clean_text"]:
            warnings.append(f"Page {page['page_number']} sans texte ; OCR non implémenté")
    languages = Counter(p["language"] for p in pages if p["language"] != "und")
    return {
        "version": VERSION,
        "pages": pages,
        "warnings": warnings,
        "language": languages.most_common(1)[0][0] if languages else "und",
    }


def chunks(
    page: dict[str, Any], asset_sha: str, settings: DocumentSettings
) -> list[dict[str, Any]]:
    text = page["clean_text"]
    if settings.chunk_overlap >= settings.chunk_chars:
        raise ValueError("Le chevauchement doit être inférieur à la taille des passages")
    rows, start = [], 0
    while start < len(text):
        end = min(len(text), start + settings.chunk_chars)
        if end < len(text):
            boundary = text.rfind(" ", start + settings.chunk_chars // 2, end)
            if boundary > start:
                end = boundary
        value = text[start:end]
        identity = f"{asset_sha}:{VERSION}:{page['page_number']}:{start}:{end}:{value}"
        rows.append(
            {
                "id": hashlib.sha256(identity.encode()).hexdigest(),
                "ordinal": len(rows),
                "start": start,
                "end": end,
                "text": value,
                "is_reference": page["reference_start"] is not None
                and start >= page["reference_start"],
            }
        )
        if end == len(text):
            break
        start = max(start + 1, end - settings.chunk_overlap)
    return rows


def extract_isolated(path: Path, format: str, settings: DocumentSettings) -> dict[str, Any]:
    # Borne le temps d'un parseur PDF indépendant du heartbeat du consommateur.
    with tempfile.TemporaryDirectory(prefix="biosentinelle-document-") as directory:
        output = Path(directory) / "extracted.json"
        config = Path(directory) / "config.json"
        config.write_text(settings.model_dump_json(exclude={"openalex_api_key"}), encoding="utf-8")
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "workers.documents.extraction",
                    str(path),
                    "--format",
                    format,
                    "--output",
                    str(output),
                    "--config",
                    str(config),
                ],
                check=True,
                timeout=120,
                capture_output=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Extraction interrompue après 120 secondes") from exc
        except subprocess.CalledProcessError as exc:
            raise ValueError(
                "Extraction impossible : " + exc.stderr.decode(errors="replace")[-1500:]
            ) from exc
        return json.loads(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--format", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    configuration = DocumentSettings.model_validate_json(args.config.read_text(encoding="utf-8"))
    args.output.write_text(
        json.dumps(extract_pages(args.path, args.format, configuration), ensure_ascii=False),
        encoding="utf-8",
    )
