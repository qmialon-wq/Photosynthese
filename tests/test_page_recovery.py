import json

import httpx
import pytest

from shared.rag.config import RagSettings
from shared.rag.synthesis import Page, Paragraph
from tests.test_synthesis_contracts import FakeGenerator, action, fixtures
from workers.documents import synthesis


def test_truncated_page_recovers_by_validated_paragraphs(monkeypatch, tmp_path):
    context = fixtures(monkeypatch, tmp_path)

    class Cutoff(FakeGenerator):
        pages_attempted = 0
        segments = 0

        def generate(self, instruction, payload, schema):
            if schema is Page:
                self.pages_attempted += 1
                raise synthesis.TruncatedResponse("Output cutoff")
            if schema is Paragraph:
                self.segments += 1
                assert payload["paragraph_index"] == len(payload["previous_paragraphs"]) + 1
                return Paragraph(
                    text=" ".join(["Conserver les haies selon le diagnostic du terrain."] * 17),
                    citations=["D1"],
                )
            return super().generate(instruction, payload, schema)

    generator = Cutoff()
    result = synthesis.synthesize({}, context, RagSettings(), lambda *a, **kw: None, generator)
    assert result["status"] == "generated"
    assert generator.pages_attempted == 4  # No repeated full-page request with the same cap.
    assert generator.segments == 12
    assert len(result["pages"]) == 4
    assert all(len(p["paragraphs"]) == 3 for p in result["pages"])
    resumed = Cutoff()
    again = synthesis.synthesize({}, context, RagSettings(), lambda *a, **kw: None, resumed)
    assert again["pages"] == result["pages"]
    assert resumed.pages_attempted == resumed.segments == 0


def test_recovery_does_not_publish_unsupported_numbers():
    class Invented:
        def generate(self, instruction, payload, schema):
            if schema is Page:
                raise synthesis.TruncatedResponse("Cutoff")
            return Paragraph(
                text=" ".join(["Conserver une bande de 50 m sans étude préalable."] * 10),
                citations=["D1"],
            )

    with pytest.raises(ValueError, match="50"):
        synthesis.write_page(
            Invented(),
            "Write",
            {"page_title": "Diagnostic", "recommendations": {"actions": [action()]}},
            lambda page: None,
            {"D1": "Hedgerow conservation."},
            {},
            lambda message: None,
        )


@pytest.mark.parametrize("schema,budget", [(Page, 2200), (Paragraph, 900)])
def test_token_budgets_and_cutoffs_are_explicit(monkeypatch, schema, budget):
    requests = []

    def transport(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={"done_reason": "length", "response": "{unfinished"})

    client = httpx.Client
    monkeypatch.setattr(
        synthesis.httpx,
        "Client",
        lambda **kw: client(transport=httpx.MockTransport(transport), **kw),
    )
    with pytest.raises(synthesis.TruncatedResponse):
        synthesis.Generator(RagSettings())._generate("Write", {"citations": ["D1"]}, schema)
    assert requests[0]["options"]["num_predict"] == budget
    if schema is Paragraph:
        assert requests[0]["format"]["properties"]["citations"]["items"]["enum"] == ["D1"]
        assert requests[0]["format"]["properties"]["text"]["maxLength"] == 1200
    else:
        assert requests[0]["format"]["properties"]["paragraphs"]["maxItems"] == 3
