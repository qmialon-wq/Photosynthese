import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from shared.documents.config import DocumentSettings
from shared.review import database


@pytest.fixture
def document_db(monkeypatch, tmp_path):
    schema = "test_documents_" + uuid4().hex
    kwargs = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "dbname": os.getenv("POSTGRES_DB", "biosentinelle"),
        "user": os.getenv("POSTGRES_USER", "biosentinelle"),
        "password": os.getenv("POSTGRES_PASSWORD", "biosentinelle_local"),
    }
    admin = psycopg.connect(**kwargs, autocommit=True)
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def connect():
        return psycopg.connect(
            **kwargs, options=f"-c search_path={schema},public -c statement_timeout=15000"
        )

    monkeypatch.setattr(database, "connect", connect)
    monkeypatch.setenv("BIOSENTINELLE_DOCUMENTS_ROOT", str(tmp_path / "documents"))
    specification = importlib.util.spec_from_file_location(
        "document_migration",
        Path("backend/migrations/versions/0006_scientific_documents.py"),
    )
    migration = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(migration)
    try:
        with connect() as connection:
            monkeypatch.setattr(migration.op, "execute", connection.execute)
            migration.upgrade()
            spec = importlib.util.spec_from_file_location(
                "document_species_migration",
                Path("backend/migrations/versions/0007_document_species.py"),
            )
            species_migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(species_migration)
            monkeypatch.setattr(species_migration.op, "execute", connection.execute)
            species_migration.upgrade()
            spec = importlib.util.spec_from_file_location(
                "document_collection_migration",
                Path("backend/migrations/versions/0008_document_collection.py"),
            )
            collection_migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(collection_migration)
            monkeypatch.setattr(collection_migration.op, "execute", connection.execute)
            collection_migration.upgrade()
        yield DocumentSettings(root=tmp_path / "documents", request_interval=0.2)
    finally:
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


@pytest.fixture
def pdf_bytes():
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    for text in [
        "Synthetic test document. The red fox uses woodland and hedgerows. " * 5,
        "References\nSynthetic Author. Test reference on biodiversity conservation.",
    ]:
        page = writer.add_blank_page(600, 800)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
            }
        )
        stream = DecodedStreamObject()
        lines = text.replace("(", "\\(").replace(")", "\\)").splitlines()
        commands = (
            "BT /F1 12 Tf 14 TL 30 700 Td " + " T* ".join(f"({line}) Tj" for line in lines) + " ET"
        )
        stream.set_data(commands.encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
        link = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/Rect"): ArrayObject([NumberObject(n) for n in (0, 0, 100, 10)]),
                NameObject("/A"): DictionaryObject(
                    {
                        NameObject("/S"): NameObject("/URI"),
                        NameObject("/URI"): TextStringObject("https://example.org/test-reference"),
                    }
                ),
            }
        )
        page[NameObject("/Annots")] = ArrayObject([writer._add_object(link)])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
