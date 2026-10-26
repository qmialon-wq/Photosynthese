import pytest

from shared.rag.grounding import numbers, quantities, validate_page
from shared.rag.synthesis import Page, Paragraph


@pytest.mark.parametrize("space", [" ", "\u00a0", "\u202f"])
def test_french_thousands_match_declared_area(space):
    text = f"Le terrain de 6{space}000 m² nécessite un diagnostic local avant les travaux."
    assert numbers(text) == {6000}
    assert quantities(text) == {(6000, "m2")}
    page = Page(title="Diagnostic territorial", paragraphs=[
        Paragraph(text=text, citations=["D1"]) for _ in range(3)
    ])
    validate_page(page, {"D1": "No quantitative prescription."}, {"area_m2": 6000})


def test_grouping_preserves_decimals_and_multiple_groups():
    assert numbers("1 234 567,50 m² et 25,5 m") == {1234567.5, 25.5}
    assert quantities("1 234 567,50 m² et 25,5 m") == {(1234567.5, "m2"), (25.5, "m")}
    assert numbers("6 et 0 ; 2024 2025 ; D6000") == {6, 0, 2024, 2025}
    assert numbers("Superficie : 6 000, soit la totalité. Total : 6 000.") == {6000}


def test_invented_area_and_unsupported_distance_still_fail():
    text = "Prévoir un espace de 7 000 m² après le diagnostic du terrain."
    page = Page(title="Diagnostic territorial", paragraphs=[
        Paragraph(text=text, citations=["D1"]) for _ in range(3)
    ])
    with pytest.raises(ValueError, match="7000"):
        validate_page(page, {"D1": "No quantitative prescription."}, {"area_m2": 6000})
    for paragraph in page.paragraphs:
        paragraph.text = "Prévoir une distance de 6 000 m après le diagnostic du terrain."
    with pytest.raises(ValueError, match="Distance"):
        validate_page(page, {"D1": "No quantitative prescription."}, {"area_m2": 6000})
