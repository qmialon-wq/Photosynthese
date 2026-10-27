from shared.parcels.citations import article_url, link_text, reference_label, source_index
from shared.parcels.report import printable_html, render_territorial


def test_sources_use_doi_pdf_and_safe_fallbacks():
    assert article_url({"doi": " https://doi.org/10.1234/a#b "}) == "https://doi.org/10.1234/a%23b"
    assert (
        article_url({"findings": [{"source_url": "https://example.org/article.pdf"}]})
        == "https://example.org/article.pdf"
    )
    assert article_url({"source_url": "javascript:alert(1)"}) is None
    assert (
        article_url({"id": "doc", "findings": [{"asset_id": "asset"}]})
        == "/api/documents/doc/assets/asset?inline=true"
    )


def test_existing_snapshot_renders_titles_and_links_without_mutating_the_audit():
    documents = [
        {
            "citation": "D319",
            "title": "Haies <et> biodiversité",
            "doi": "10.1234/hedges",
            "chunks_read": 1,
            "relevance": "accepted",
            "quality": "accepted",
            "findings": [],
        },
        {
            "citation": "D2",
            "title": "Vie urbaine",
            "doi": None,
            "chunks_read": 1,
            "relevance": "accepted",
            "quality": "accepted",
            "source_url": "https://example.org/article.pdf",
            "findings": [],
        },
    ]
    report = {
        "status": "generated",
        "coverage": {"documents_read": 2, "documents_total": 2},
        "ledger": documents,
        "actions": [],
        "pages": [
            {
                "title": "Diagnostic",
                "paragraphs": [
                    {"text": "Selon [D319], conserver les haies.", "citations": ["D319", "D2"]}
                ],
            }
            for _ in range(4)
        ],
    }
    data = {
        "territorial_report": report,
        "profile": {"area_m2": 6000, "locality": "Caen"},
        "land_label": "Prairie",
        "project_label": "Logement",
        "limitations": [],
    }
    html = printable_html(data)
    assert html.count('<section class="page') == 4
    assert html.count('href="https://doi.org/10.1234/hedges"') == 4
    assert 'target="_blank" rel="noopener noreferrer"' in html
    assert "Haies &lt;et&gt; biodiversité" in html and "<et>" not in html
    assert "[D319]" not in html
    assert "https://example.org/article.pdf" in html
    assert (
        "[Haies &lt;et&gt; biodiversité](<https://doi.org/10.1234/hedges>)"
        in render_territorial(data, markdown=True)
    )
    assert "Haies <et> biodiversité (https://doi.org/10.1234/hedges)" in render_territorial(data)
    assert report["pages"][0]["paragraphs"][0]["text"].startswith("Selon [D319]")


def test_untrusted_text_titles_and_unknown_references_stay_escaped():
    sources = source_index(
        {
            "ledger": [
                {
                    "citation": "D1",
                    "title": '<img src=x onerror="evil()">',
                    "source_url": "javascript:alert(1)",
                }
            ]
        }
    )
    rendered = link_text("<script>evil()</script> [D1]", sources)
    assert "<script>" not in rendered and "<img" not in rendered
    assert "href=" not in rendered
    assert "&lt;img" in rendered
    assert "<script>" not in reference_label("<script>", sources)
