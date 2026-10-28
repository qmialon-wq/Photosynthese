"""Traduction locale anglais-français, originale conservée, reprise et cache par page."""

import hashlib
import json
import re
import time
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from shared.documents import service
from shared.documents.config import DocumentSettings
from shared.review.database import jsonb
from shared.task_priority import TaskDeferred, document_checkpoint

from .http import SafeHTTP
from .storage import DocumentStorage

MODEL_URL = "https://data.argosopentech.com/argospm/v1/translate-en_fr-1_9.argosmodel"
MODEL_SHA = "3a65ed83364f4e7b06e30f9dd823db1934899ed3ce839e63f46dc7b09dc797b4"
ENGINE = "argos-opus-en-fr-1.9-ctranslate2-int8-v1"
FILES = [
    "metadata.json",
    "README.md",
    "sentencepiece.model",
    "model/config.json",
    "model/model.bin",
    "model/shared_vocabulary.json",
]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def prepare_model(settings: DocumentSettings, http: SafeHTTP) -> Path:
    storage = DocumentStorage(settings.translation_model_root)
    directory = storage.path("argos-en-fr-1.9")
    manifest = directory / "integrity.json"
    if manifest.is_file():
        hashes = json.loads(manifest.read_text())
        if hashes.get("archive_sha256") != MODEL_SHA:
            raise ValueError("Version du modèle de traduction incompatible")
        for name in FILES:
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != hashes["files"][name]:
                raise ValueError("Modèle de traduction corrompu : " + name)
        return directory
    archive = storage.path("translate-en_fr-1_9.argosmodel")
    if not archive.is_file():
        data, _, _ = http.get(MODEL_URL, cache=False, max_bytes=128 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != MODEL_SHA:
            raise ValueError("Empreinte SHA-256 du modèle de traduction incorrecte")
        storage.write(archive.name, data)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != MODEL_SHA:
        raise ValueError("Archive de traduction corrompue")
    hashes = {}
    with zipfile.ZipFile(archive) as package:
        for name in FILES:
            item = package.getinfo("translate-en_fr-1_9/" + name)
            if item.file_size > 256 * 1024 * 1024:
                raise ValueError("Fichier de modèle trop volumineux")
            content = package.read(item)
            storage.write("argos-en-fr-1.9/" + name, content)
            hashes[name] = hashlib.sha256(content).hexdigest()
    storage.json("argos-en-fr-1.9/integrity.json", {"archive_sha256": MODEL_SHA, "files": hashes})
    return directory


class LocalTranslator:
    def __init__(self, directory: Path) -> None:
        import ctranslate2
        import sentencepiece

        self.tokenizer = sentencepiece.SentencePieceProcessor(
            model_file=str(directory / "sentencepiece.model")
        )
        self.model = ctranslate2.Translator(
            str(directory / "model"),
            device="cpu",
            compute_type="int8",
            inter_threads=1,
            intra_threads=2,
        )

    def segments(self, text: str) -> list[str]:
        if len(self.tokenizer.encode(text)) <= 256:
            return [text]
        midpoint = len(text) // 2
        boundary = text.rfind(" ", 0, midpoint) if " " in text[:midpoint] else midpoint
        boundary = max(1, boundary)
        return self.segments(text[:boundary]) + self.segments(text[boundary:].lstrip())

    def translate(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if not line.strip():
                lines.append("")
                continue
            sentences = [
                segment
                for sentence in re.split(r"(?<=[.!?])\s+", line.strip())
                for segment in self.segments(sentence)
                if segment.strip()
            ]
            results = self.model.translate_batch(
                [self.tokenizer.encode(sentence, out_type=str) for sentence in sentences],
                beam_size=2,
                max_batch_size=8,
                max_input_length=0,
                max_decoding_length=768,
                replace_unknowns=True,
            )
            translated = []
            for result in results:
                if len(result.hypotheses[0]) >= 768:
                    raise ValueError("Traduction interrompue avant la fin du passage")
                value = (
                    self.tokenizer.decode(result.hypotheses[0]).replace("▁", " ").replace("_", " ")
                )
                if not value.strip():
                    raise ValueError("Le moteur a produit une traduction vide")
                translated.append(value)
            lines.append(" ".join(translated))
        return "\n".join(lines)


@lru_cache(maxsize=1)
def engine(directory: str) -> LocalTranslator:
    return LocalTranslator(Path(directory))


def queue(document_id: str) -> None:
    document = service.document(document_id)
    if document["status"] != "indexed":
        return
    with service.transaction() as connection:
        rows = connection.execute(
            """SELECT a.sha256 FROM document_assets a
          WHERE a.document_id=%s ORDER BY a.sha256""",
            (document["id"],),
        ).fetchall()
    fingerprint = digest(document["title"] + str(document["abstract"]) + str(rows))
    if not document["metadata"].get("translation_fr"):
        with service.transaction() as connection:
            connection.execute(
                "UPDATE scientific_documents SET "
                "metadata=jsonb_set(metadata,'{translation_fr}',%s) "
                "WHERE id=%s",
                (jsonb({"status": "queued", "engine": ENGINE}), document["id"]),
            )
    service.submit(
        "translate",
        {"document_id": str(document["id"])},
        "automatic-translation",
        dedup_key=f"translation:{document['id']}:{ENGINE}:{fingerprint}",
    )


def run(document_id: str, settings: DocumentSettings, http: SafeHTTP, task: str) -> dict[str, Any]:
    document = service.document(document_id)
    identifier = str(document["id"])
    started = time.perf_counter()

    def state(status: str, **extra: Any) -> None:
        value = {"status": status, "engine": ENGINE, "source_title": document["title"], **extra}
        with service.transaction() as connection:
            connection.execute(
                "UPDATE scientific_documents SET "
                "metadata=jsonb_set(metadata,'{translation_fr}',%s) "
                "WHERE id=%s",
                (jsonb(value), identifier),
            )

    with service.transaction() as connection:
        eligible = connection.execute(
            """SELECT 1 WHERE NOT EXISTS(
          SELECT 1 FROM document_species WHERE document_id=%s)
          OR EXISTS(SELECT 1 FROM document_species WHERE document_id=%s AND NOT excluded)""",
            (identifier, identifier),
        ).fetchone()
        pages = connection.execute(
            """SELECT p.*,t.translated_text,t.source_sha256,t.engine
          FROM document_pages p JOIN document_assets a ON a.id=p.asset_id
          LEFT JOIN document_page_translations t USING(asset_id,page_number)
          WHERE a.document_id=%s ORDER BY a.id,p.page_number""",
            (identifier,),
        ).fetchall()
    if document["status"] == "rejected" or not eligible or not pages:
        return {"skipped": True}
    if document["language"] == "fr":
        state("original_fr")
        return {"document_id": identifier, "original_fr": True}
    if document["language"] != "en":
        state(
            "unsupported",
            error="Seule la traduction anglais → français est disponible actuellement.",
        )
        return {"document_id": identifier, "unsupported": True}
    state("running", pages_done=0, pages_total=len(pages))
    try:
        document_checkpoint(task, 3)
        translator = engine(str(prepare_model(settings, http)))
        title = translator.translate(document["title"])
        abstract = translator.translate(document["abstract"]) if document["abstract"] else None
        for index, page in enumerate(pages):
            document_checkpoint(task, 3)
            source_hash = digest(page["clean_text"])
            if page["source_sha256"] != source_hash or page["engine"] != ENGINE:
                language = page["language"] if page["language"] != "und" else document["language"]
                if language not in ("en", "fr"):
                    raise ValueError(f"Langue de la page {page['page_number']} non prise en charge")
                text = (
                    translator.translate(page["clean_text"])
                    if language == "en" and page["clean_text"].strip()
                    else page["clean_text"]
                )
                with service.transaction() as connection:
                    connection.execute(
                        """INSERT INTO document_page_translations
                      (asset_id,page_number,source_text,source_sha256,translated_text,engine)
                      VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(asset_id,page_number) DO UPDATE SET
                      source_text=excluded.source_text,source_sha256=excluded.source_sha256,
                      translated_text=excluded.translated_text,engine=excluded.engine,created_at=now()""",
                        (
                            page["asset_id"],
                            page["page_number"],
                            page["clean_text"],
                            source_hash,
                            text,
                            ENGINE,
                        ),
                    )
            state(
                "running",
                title=title,
                abstract=abstract,
                pages_done=index + 1,
                pages_total=len(pages),
            )
            service.event(
                task, "translation", f"Page {index + 1}/{len(pages)} traduite", document=identifier
            )
        # Export dérivé téléchargeable, sans modifier l'original ou les passages du futur RAG.
        with service.transaction() as connection:
            translations = connection.execute(
                """SELECT t.translated_text,p.page_number,a.license
              FROM document_page_translations t
              JOIN document_pages p USING(asset_id,page_number)
              JOIN document_assets a ON a.id=p.asset_id
              WHERE a.document_id=%s AND t.source_text=p.clean_text ORDER BY a.id,p.page_number""",
                (identifier,),
            ).fetchall()
        DocumentStorage(settings.root).write(
            f"translations/{identifier}/fr.txt",
            (
                title
                + "\nTitre original : "
                + document["title"]
                + "\nAuteurs : "
                + ", ".join(document["authors"])
                + "\nDOI : "
                + (document["doi"] or "non renseigné")
                + "\nLicences des originaux : "
                + ", ".join(sorted({p["license"] for p in translations}))
                + "\nTraduction automatique : "
                + ENGINE
                + "\n\n"
                + "\n\n".join(
                    f"Page {p['page_number']}\n{p['translated_text']}" for p in translations
                )
            ).encode(),
        )
        state(
            "completed",
            title=title,
            abstract=abstract,
            pages_done=len(pages),
            pages_total=len(pages),
        )
        return {
            "document_id": identifier,
            "pages": len(pages),
            "seconds": round(time.perf_counter() - started, 3),
        }
    except TaskDeferred:
        state("queued", pages_done=index if "index" in locals() else 0, pages_total=len(pages))
        raise
    except Exception as exc:
        state("error", error=str(exc)[:1000])
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Diagnostic de traduction locale anglais-français")
    parser.add_argument(
        "--text", default="Wildlife crossings reduce the impact of roads on animals."
    )
    args = parser.parse_args()
    settings = DocumentSettings()
    http = SafeHTTP(settings)
    try:
        translator = engine(str(prepare_model(settings, http)))
        print(translator.translate(args.text))
    finally:
        http.close()
