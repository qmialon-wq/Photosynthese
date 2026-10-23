import os

import pytest

from shared.documents.config import DocumentSettings
from shared.documents.schemas import Search
from workers.documents.http import SafeHTTP
from workers.documents.sources import SOURCES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("BIOSENTINELLE_LIVE_DOCUMENTS") != "1",
        reason="Activer explicitement le diagnostic des API réelles",
    ),
]


@pytest.mark.parametrize("source", ["openalex", "crossref", "europepmc"])
def test_real_scientific_species_search(tmp_path, source):
    http = SafeHTTP(DocumentSettings(root=tmp_path))
    try:
        rows = list(
            SOURCES[source](http).search(
                Search(
                    species=["Vulpes vulpes"],
                    topics=["ecology"],
                    sources=[source],
                    limit_per_source=1,
                )
            )
        )
        assert rows and rows[0].title and rows[0].source_id
        assert rows[0].source == source
    finally:
        http.close()
