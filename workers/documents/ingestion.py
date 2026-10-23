"""Découverte isolant les erreurs, fichiers autorisés et indexation textuelle réelle."""

import hashlib
import logging
from typing import Any
from uuid import uuid4

from shared.documents import service
from shared.documents.config import DocumentSettings
from shared.documents.corpus import discover
from shared.documents.relevance import screen
from shared.documents.schemas import FullText, ManualImport, Publication, Search
from shared.review.database import jsonb

from .extraction import VERSION, chunks, extract_isolated
from .http import FetchError, SafeHTTP
from .sources import SOURCES, Crossref, license_code
from .storage import DocumentStorage
from .translation import queue as queue_translation

logger = logging.getLogger(__name__)


class Ingestor:
    def __init__(self, settings: DocumentSettings, http: SafeHTTP, task: str) -> None:
        self.settings, self.http, self.task = settings, http, task
        self.storage = DocumentStorage(settings.root)

    def log(
        self,
        stage: str,
        message: str,
        *,
        document: str | None = None,
        level: str = "info",
        data: dict[str, Any] | None = None,
    ) -> None:
        service.event(self.task, stage, message, document=document, level=level, data=data)

    def asset(
        self,
        identifier: str,
        data: bytes,
        format: str,
        license: str,
        evidence: dict[str, Any],
        url: str | None = None,
    ) -> str:
        digest, key = self.storage.content(data, format)
        with service.transaction(write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM document_assets WHERE sha256=%s", (digest,)
            ).fetchone()
            if existing:
                service.merge(connection, str(existing["document_id"]), identifier)
                return str(existing["id"])
            asset_id = str(uuid4())
            connection.execute(
                """INSERT INTO document_assets
                (id,document_id,sha256,storage_key,format,source_url,license,rights_evidence,byte_size)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    asset_id,
                    identifier,
                    digest,
                    key,
                    format,
                    url,
                    license,
                    jsonb(evidence),
                    len(data),
                ),
            )
            connection.execute(
                "UPDATE scientific_documents SET processing_status='imported',updated_at=now(), "
                "quality=CASE WHEN quality='accepted' THEN 'pending' ELSE quality END "
                "WHERE id=%s",
                (identifier,),
            )
        self.log(
            "import",
            "Fichier conservé et vérifié par SHA-256",
            document=identifier,
            data={"asset_id": asset_id, "sha256": digest, "license": license},
        )
        return asset_id

    def index(self, asset_id: str) -> dict[str, Any]:
        with service.transaction() as connection:
            asset = connection.execute(
                "SELECT * FROM document_assets WHERE id=%s", (asset_id,)
            ).fetchone()
        if asset is None:
            raise ValueError("Fichier documentaire absent")
        path = self.storage.path(asset["storage_key"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError("Empreinte du document stocké incompatible")
        if asset["extraction_version"] == VERSION:
            queue_translation(str(asset["document_id"]))
            self.log("index", "Index existant réutilisé", document=str(asset["document_id"]))
            return {"asset_id": asset_id, "cached": True}
        extracted = extract_isolated(path, asset["format"], self.settings)
        count = 0
        with service.transaction(write=True) as connection:
            connection.execute("DELETE FROM document_chunks WHERE asset_id=%s", (asset_id,))
            connection.execute("DELETE FROM document_pages WHERE asset_id=%s", (asset_id,))
            for page in extracted["pages"]:
                connection.execute(
                    """INSERT INTO document_pages
                    (asset_id,page_number,raw_text,clean_text,language,references_data)
                    VALUES(%s,%s,%s,%s,%s,%s)""",
                    (
                        asset_id,
                        page["page_number"],
                        page["raw_text"],
                        page["clean_text"],
                        page["language"],
                        jsonb(page["references"]),
                    ),
                )
                for chunk in chunks(page, asset["sha256"], self.settings):
                    connection.execute(
                        """INSERT INTO document_chunks
                        (id,asset_id,page_number,ordinal,start_char,end_char,text,language,is_reference)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            chunk["id"],
                            asset_id,
                            page["page_number"],
                            chunk["ordinal"],
                            chunk["start"],
                            chunk["end"],
                            chunk["text"],
                            page["language"],
                            chunk["is_reference"],
                        ),
                    )
                    count += 1
            connection.execute(
                """UPDATE document_assets SET extraction_version=%s,
                extraction_warnings=%s WHERE id=%s""",
                (VERSION, jsonb(extracted["warnings"]), asset_id),
            )
            connection.execute(
                """UPDATE scientific_documents SET processing_status=%s,language=%s,
                updated_at=now() WHERE id=%s""",
                ("indexed" if count else "imported", extracted["language"], asset["document_id"]),
            )
        self.storage.json(f"extracted/{asset['sha256']}/{VERSION}.json", extracted)
        queue_translation(str(asset["document_id"]))
        self.log(
            "index",
            "Extraction terminée",
            document=str(asset["document_id"]),
            data={
                "pages": len(extracted["pages"]),
                "chunks": count,
                "warnings": extracted["warnings"],
            },
        )
        return {
            "asset_id": asset_id,
            "pages": len(extracted["pages"]),
            "chunks": count,
            "warnings": extracted["warnings"],
        }

    def fetch(self, identifier: str) -> dict[str, Any]:
        document = service.document(identifier)
        identifier = str(document["id"])
        if document["status"] == "rejected":
            self.log("download", "Document rejeté : téléchargement ignoré", document=identifier)
            return {"document_id": identifier, "skipped": True}
        with service.transaction() as connection:
            assets = connection.execute(
                "SELECT id FROM document_assets WHERE document_id=%s", (identifier,)
            ).fetchall()
        if assets:
            return {"document_id": identifier, "assets": [self.index(str(a["id"])) for a in assets]}
        failures = []
        for raw in document["metadata"].get("fulltexts", []):
            candidate = FullText.model_validate(raw)
            if not license_code(candidate.license):
                continue
            try:
                data, _, final_url = self.http.get(candidate.url, cache=False)
                effective_license = candidate.license
                if candidate.format == "pdf" and not data.lstrip().startswith(b"%PDF-"):
                    raise FetchError("La réponse n'est pas un PDF ; aucun formulaire d'accès suivi")
                if candidate.format == "xml":
                    from defusedxml import ElementTree

                    root = ElementTree.fromstring(data)
                    references = []
                    for element in root.findall("./front/article-meta/permissions/license"):
                        references.extend(element.attrib.values())
                        references.extend(
                            e.attrib.get("{http://www.w3.org/1999/xlink}href", "")
                            for e in element.iter()
                        )
                    licenses = {license_code(value) for value in references} - {None}
                    if license_code(candidate.license) not in licenses:
                        raise FetchError("XML sans licence ouverte vérifiable dans le fichier")
                    effective_license = license_code(candidate.license)
                asset = self.asset(
                    identifier,
                    data,
                    candidate.format,
                    effective_license,
                    {
                        "metadata_evidence": candidate.evidence,
                        "declared_url": candidate.url,
                        "final_url": final_url,
                        "task_id": self.task,
                    },
                    final_url,
                )
                return {"document_id": identifier, **self.index(asset)}
            except Exception as exc:
                self.log(
                    "download",
                    f"Copie indisponible : {type(exc).__name__}: {str(exc)[:1000]}",
                    document=identifier,
                    level="warning",
                )
                failures.append(type(exc).__name__)
        with service.transaction(write=True) as connection:
            # Un fichier déjà importé n'est pas effacé par un échec de parsing.
            connection.execute(
                """UPDATE scientific_documents SET processing_status='inaccessible',updated_at=now()
                WHERE id=%s AND NOT EXISTS(SELECT 1 FROM document_assets WHERE document_id=%s)""",
                (identifier, identifier),
            )
        self.log(
            "download",
            "Texte intégral non conservé : licence inconnue/non autorisée ou accès indisponible",
            document=identifier,
            level="warning",
            data={"failures": failures},
        )
        return {"document_id": identifier, "inaccessible": True, "failures": failures}

    def manual(self, request: dict[str, Any], actor: str) -> dict[str, Any]:
        imported = ManualImport.model_validate(request)
        path = DocumentStorage(self.settings.root / "inbox").path(imported.path)
        if not path.is_file() or path.stat().st_size > self.settings.max_file_bytes:
            raise ValueError("Fichier manuel absent ou trop volumineux")
        data = path.read_bytes()
        format = path.suffix.lower().lstrip(".")
        if format == "pdf" and not data.lstrip().startswith(b"%PDF-"):
            raise ValueError("Le fichier fourni n'est pas un PDF")
        digest = hashlib.sha256(data).hexdigest()
        publication = Publication(
            source="manual",
            source_id=digest,
            title=imported.title or path.name,
            doi=imported.doi,
            license=imported.license,
            identifiers={"sha256": digest},
            raw={"filename": imported.path, "actor": actor, "rights_confirmed": True},
        )
        identifier = service.register(publication, self.task)
        discover(identifier, imported.species, actor)
        asset = self.asset(
            identifier,
            data,
            format,
            imported.license or "user-authorized-local",
            {
                "actor": actor,
                "rights_confirmed": True,
                "source_key": imported.path,
                "task_id": self.task,
            },
        )
        return {"document_id": str(service.document(identifier)["id"]), **self.index(asset)}

    def search(self, request: dict[str, Any]) -> dict[str, Any]:
        query = Search.model_validate(request["search"])
        actor = service.task(self.task)["actor"]
        counts = {"observed": 0, "errors": 0, "sources_ok": 0, "inaccessible": 0, "filtered_out": 0}
        counts["downloaded"] = 0
        documents: set[str] = set()
        for source_name in query.sources:
            self.log(
                "source",
                "Début du passage",
                data={"source": source_name, "query": query.model_dump()},
            )
            try:
                source = SOURCES[source_name](self.http)
                accepted = 0
                for publication in source.search(query):
                    if accepted >= query.limit_per_source:
                        break
                    try:
                        screening = (
                            screen(publication, query)
                            if query.focus == "human_activities"
                            else None
                        )
                        if screening and not screening["candidate"]:
                            counts["filtered_out"] += 1
                            self.log(
                                "relevance",
                                "Notice hors ciblage ou métadonnées insuffisantes",
                                data={
                                    "source": source_name,
                                    "source_id": publication.source_id,
                                    "title": publication.title,
                                    "screening": screening,
                                },
                            )
                            continue
                        if query.download_fulltext and not publication.fulltexts:
                            # Une notice Crossref peut enrichir une copie déjà importée,
                            # mais ne prouve pas qu'un texte soit téléchargeable.
                            counts["inaccessible"] += 1
                            continue
                        identifier = service.register(
                            publication, self.task, request.get("watch_id")
                        )
                        documents.add(identifier)
                        discover(identifier, query.species, actor)
                        if request.get("collection_species"):
                            with service.transaction() as connection:
                                excluded = connection.execute(
                                    """SELECT 1 FROM document_species
                                  WHERE document_id=%s AND species=%s AND excluded""",
                                    (
                                        service.document(identifier)["id"],
                                        request["collection_species"],
                                    ),
                                ).fetchone()
                            if excluded:
                                continue
                        counts["observed"] += 1
                        accepted += int(not query.download_fulltext)
                        if screening:
                            with service.transaction() as connection:
                                connection.execute(
                                    "UPDATE scientific_documents SET metadata=metadata || %s "
                                    "WHERE id=%s",
                                    (jsonb({"screening": screening}), identifier),
                                )
                            self.log(
                                "relevance",
                                "Candidat activités humaines et impacts sur la faune",
                                document=identifier,
                                data=screening,
                            )
                        if source_name != "crossref" and publication.doi:
                            try:
                                complement = Crossref(self.http).lookup(publication.doi)
                                service.register(complement, self.task, request.get("watch_id"))
                            except Exception as exc:
                                self.log(
                                    "enrichment",
                                    f"Complément Crossref indisponible : {type(exc).__name__}",
                                    document=identifier,
                                    level="warning",
                                )
                                counts["errors"] += 1
                        if query.download_fulltext:
                            result = self.fetch(identifier)
                            counts["inaccessible"] += int(result.get("inaccessible", False))
                            if not result.get("inaccessible") and not result.get("skipped"):
                                counts["downloaded"] += 1
                                accepted += 1
                    except Exception as exc:
                        counts["errors"] += 1
                        self.log(
                            "publication",
                            f"Notice ignorée : {type(exc).__name__}: {str(exc)[:1000]}",
                            level="error",
                        )
                counts["sources_ok"] += 1
                counts["errors"] += getattr(source, "errors", 0)
            except Exception as exc:
                counts["errors"] += 1
                self.log(
                    "source",
                    f"Source indisponible : {type(exc).__name__}: {str(exc)[:1000]}",
                    level="error",
                    data={"source": source_name},
                )
        return {**counts, "document_ids": sorted(documents)}

    def perform(self, kind: str, request: dict[str, Any], actor: str) -> dict[str, Any]:
        if kind == "search":
            return self.search(request)
        if kind == "import":
            return self.manual(request, actor)
        if kind == "fetch":
            return self.fetch(request["document_id"])
        if kind == "index":
            return self.index(request["asset_id"])
        if kind == "translate":
            from .translation import run

            return run(request["document_id"], self.settings, self.http, self.task)
        raise ValueError("Type de tâche documentaire inconnu")
