import pytest

from shared.documents.config import DocumentSettings
from workers.documents.extraction import chunks, extract_pages


def test_real_pdf_pages_links_language_and_reproducible_chunks(tmp_path, pdf_bytes):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(pdf_bytes)
    settings = DocumentSettings(root=tmp_path, chunk_chars=200, chunk_overlap=30)
    result = extract_pages(path, "pdf", settings)
    assert len(result["pages"]) == 2 and result["language"] == "en"
    first, second = result["pages"]
    assert "red fox" in first["raw_text"] and first["page_number"] == 1
    assert first["references"][0]["url"].startswith("https://example.org/")
    rows = chunks(first, "test-sha", settings)
    assert rows == chunks(first, "test-sha", settings)
    assert all(first["clean_text"][r["start"] : r["end"]] == r["text"] for r in rows)
    assert second["reference_start"] is not None


def test_xml_entities_are_rejected_and_blank_pdf_does_not_fake_text(tmp_path):
    from io import BytesIO

    from defusedxml.common import DefusedXmlException
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    buffer = BytesIO()
    writer.write(buffer)
    path = tmp_path / "blank.pdf"
    path.write_bytes(buffer.getvalue())
    result = extract_pages(path, "pdf", DocumentSettings(root=tmp_path))
    assert not result["pages"][0]["clean_text"] and result["warnings"]
    xml = tmp_path / "unsafe.xml"
    xml.write_text(
        '<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><article><body>&a;</body></article>'
    )
    with pytest.raises(DefusedXmlException):
        extract_pages(xml, "xml", DocumentSettings(root=tmp_path))
