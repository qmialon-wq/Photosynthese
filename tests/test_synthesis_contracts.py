import pytest

from shared.parcels.report import printable_html
from shared.rag.config import RagSettings
from shared.rag.grounding import validate_actions, validate_page
from shared.rag.synthesis import Actions, Finding, Notes, Page, Paragraph
from workers.documents import synthesis


def action(citations=None):
    return {
        "title": "Conserver les haies existantes",
        "action": "Conserver les haies existantes et adapter les accès au relevé de terrain.",
        "location": "Sur les bordures existantes, à cartographier avant implantation.",
        "rationale": "Les résultats justifient de comparer des variantes conservant les haies.",
        "conditions": "À confirmer par un relevé du terrain et une vérification des usages locaux.",
        "priority": "design",
        "monitoring": "Relever les ruptures de continuité avant et après travaux.",
        "citations": citations or ["D1"],
    }


class FakeGenerator:
    settings = RagSettings()

    def __init__(self):
        self.seen = []

    def generate(self, instruction, payload, schema):
        if schema is Notes:
            self.seen.extend({row["quote_id"].rsplit(":", 1)[0] for row in payload["evidence"]})
            row = payload["evidence"][0]
            return Notes(
                findings=[
                    Finding(
                        quote_id=row["quote_id"],
                        finding="Conserver les limites végétales selon les usages du site.",
                        limits="Les effets négatifs et les différences locales restent à examiner.",
                        direction="mixed",
                    )
                ],
                relevance="Pertinent pour les haies et les accès du projet.",
            )
        if schema is Actions:
            return Actions(actions=[action() for _ in range(3)])
        assert schema is Page
        return Page(
            title=payload["page_title"],
            paragraphs=[
                Paragraph(
                    text=" ".join(
                        [
                            "Conserver les haies suppose un relevé du terrain "
                            "et une comparaison des variantes."
                        ]
                        * 7
                    ),
                    citations=["D1"],
                )
                for _ in range(3)
            ],
        )


def fixtures(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOSENTINELLE_DOCUMENTS_ROOT", str(tmp_path))
    documents = [
        {
            "id": str(i),
            "title": f"Article {i}",
            "citation": f"D{i}",
            "doi": None,
            "relevance": "pending",
            "quality": "pending",
            "chunk_count": 12,
        }
        for i in (1, 2)
    ]
    monkeypatch.setattr(synthesis, "corpus", lambda species: documents if species else [])
    monkeypatch.setattr(
        synthesis,
        "chunks",
        lambda doc: iter(
            [
                {
                    "id": f"{doc['id']}-{i}",
                    "text": (
                        "We recommend preserving existing hedgerows in agricultural landscapes. "
                        * 20
                    ),
                    "page_number": i + 1,
                    "asset_id": "asset",
                    "sha256": "hash",
                    "license": "cc-by",
                    "source_url": "https://example.org/article",
                }
                for i in range(12)
            ]
        ),
    )
    return {"confirmed_species": [], "predicted_species": [{"name": "renards"}]}


def test_all_documents_all_batches_and_cache_are_used(monkeypatch, tmp_path):
    context = fixtures(monkeypatch, tmp_path)
    generator = FakeGenerator()
    result = synthesis.synthesize(
        {"area_m2": 2500},
        context,
        RagSettings(),
        lambda *a, **kw: None,
        generator,
    )
    assert result["status"] == "generated"
    assert len(result["pages"]) == 4
    assert set(generator.seen) == {f"{d}-{i}" for d in (1, 2) for i in range(12)}
    assert result["coverage"]["chunks_read"] == 24
    assert result["coverage"]["documents_read"] == 2
    assert result["coverage"]["documents_pending_review"] == 2
    assert all(d["assessments"] for d in result["ledger"])
    generator.seen.clear()
    for row in synthesis.corpus(["renards"]):
        row["relevance"] = row["quality"] = "accepted"
        row["status"] = "indexed"
    synthesis.synthesize(
        {"area_m2": 3500}, context, RagSettings(), lambda *a, **kw: None, generator
    )
    assert not generator.seen  # Verified notes resume without rereading the model input.


def test_empty_species_never_reads_all_species_corpus(monkeypatch, tmp_path):
    fixtures(monkeypatch, tmp_path)
    result = synthesis.synthesize(
        {},
        {"confirmed_species": [], "predicted_species": []},
        RagSettings(),
        lambda *a, **kw: None,
        FakeGenerator(),
    )
    assert result["status"] == "no_sources"


def test_withdrawal_during_generation_prevents_publication(monkeypatch, tmp_path):
    context = fixtures(monkeypatch, tmp_path)
    original = synthesis.corpus
    calls = []

    def current(species):
        calls.append(True)
        return original(species) if len(calls) == 1 else []

    monkeypatch.setattr(synthesis, "corpus", current)
    with pytest.raises(ValueError, match="retiré, rejeté ou fusionné"):
        synthesis.synthesize({}, context, RagSettings(), lambda *a, **kw: None, FakeGenerator())


def test_invented_or_modified_quotes_and_unknown_references_fail():
    notes = Notes(
        findings=[
            Finding(
                chunk_id="unknown",
                quote="An invented scientific quote.",
                finding="Un résultat inventé.",
                limits="Limites inconnues.",
                direction="uncertain",
            )
        ],
        relevance="Pertinence inconnue.",
    )
    with pytest.raises(ValueError, match="Citation inventée"):
        synthesis.verified(notes, [{"id": "real", "text": "The original evidence."}])
    with pytest.raises(ValueError, match="Référence inconnue"):
        synthesis.checked_citations(Actions(actions=[action(["D999"]) for _ in range(3)]), {"D1"})


def test_oversized_chunk_is_not_silently_truncated():
    with pytest.raises(ValueError, match="Passage trop long"):
        list(synthesis.batches(iter([{"text": "x" * 10001}])))


def test_quote_selection_copies_exact_source_and_rejects_unknown_index():
    source = "We recommend preserving hedgerows.\n" + "Long unmodified source sentence. " * 60
    units = synthesis.quote_units(source)
    assert all(len(unit) <= 900 for unit in units)
    assert "".join("".join(units).split()) == "".join(source.split())
    notes = Notes(
        findings=[
            Finding(
                chunk_id="real",
                quote_index=1,
                finding="Conserver les haies existantes.",
                limits="À vérifier selon les usages locaux.",
                direction="benefit",
            )
        ],
        relevance="Document pertinent.",
    )
    synthesis.verified(notes, [{"id": "real", "text": source}])
    assert notes.findings[0].quote == units[1]
    assert notes.findings[0].finding == units[1]
    notes.findings[0].quote = ""
    notes.findings[0].quote_index = 999
    with pytest.raises(ValueError, match="Indice de citation inconnu"):
        synthesis.verified(notes, [{"id": "real", "text": source}])


def test_findings_without_justifiable_action_do_not_force_recommendations(monkeypatch, tmp_path):
    context = fixtures(monkeypatch, tmp_path)

    class NoAction(FakeGenerator):
        def generate(self, instruction, payload, schema):
            if schema is Actions:
                return Actions(actions=[])
            return super().generate(instruction, payload, schema)

    result = synthesis.synthesize({}, context, RagSettings(), lambda *a, **kw: None, NoAction())
    assert result["status"] == "no_actionable_evidence"
    assert result["coverage"]["documents_read"] == 2
    assert "pages" not in result


def test_assessments_do_not_masquerade_as_territorial_measures(monkeypatch, tmp_path):
    context = fixtures(monkeypatch, tmp_path)

    class AssessmentOnly(FakeGenerator):
        def generate(self, instruction, payload, schema):
            if schema is Actions:
                return Actions(
                    actions=[
                        {
                            **action(),
                            "action_type": "assessment",
                            "action": "Évaluer les haies et étudier les marges de la parcelle.",
                        }
                    ]
                )
            return super().generate(instruction, payload, schema)

    result = synthesis.synthesize(
        {}, context, RagSettings(), lambda *a, **kw: None, AssessmentOnly()
    )
    assert result["status"] == "no_actionable_evidence"


def test_printable_report_has_four_pages_and_escapes_publication_text():
    report = {
        "status": "generated",
        "coverage": {"documents_read": 2, "documents_total": 2},
        "pages": [
            {
                "title": "<script>alert(1)</script>",
                "paragraphs": [
                    {"text": "<img src=x onerror=alert(1)>", "citations": ["D1"]},
                ],
            }
            for _ in range(4)
        ],
    }
    data = {
        "territorial_report": report,
        "profile": {"area_m2": 1000, "locality": "Caen"},
        "land_label": "Prairie",
        "project_label": "Habitation",
    }
    html = printable_html(data)
    assert html.count('<section class="page">') == 4
    assert "<script>" not in html and "<img " not in html
    assert "&lt;script&gt;" in html
    assert "Page 4/4" in html


def test_gpu_drafting_respects_the_vision_lock(monkeypatch, tmp_path):
    from workers.vision.biosentinelle_vision.errors import GpuBusyError
    from workers.vision.biosentinelle_vision.storage.gpu import exclusive_gpu

    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    path = tmp_path / "results/.vision-gpu.lock"
    generator = synthesis.Generator(RagSettings(generation_device="cuda"))
    with exclusive_gpu("cuda", path), pytest.raises(GpuBusyError):
        generator.generate("No network call should start", {}, Notes)


def test_gpu_model_is_unloaded_before_releasing_lock(monkeypatch, tmp_path):
    from workers.vision.biosentinelle_vision.errors import GpuBusyError
    from workers.vision.biosentinelle_vision.storage.gpu import exclusive_gpu

    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    lock = tmp_path / "results/.vision-gpu.lock"
    unloaded = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, *, json):
            assert json["keep_alive"] == 0
            with pytest.raises(GpuBusyError), exclusive_gpu("cuda", lock):
                pass
            unloaded.append(True)
            return self

        def raise_for_status(self):
            pass

    monkeypatch.setattr(synthesis.httpx, "Client", Client)
    generator = synthesis.Generator(RagSettings(generation_device="cuda"))
    monkeypatch.setattr(generator, "_generate", lambda *args: "test")
    assert generator.generate("test", {}, Notes) == "test"
    assert unloaded == [True]
    with exclusive_gpu("cuda", lock):
        pass


def test_context_is_expanded_instead_of_silently_truncating_evidence(monkeypatch):
    import json

    import httpx

    contexts = []

    def transport(request):
        body = json.loads(request.content)
        contexts.append(body["options"]["num_ctx"])
        return httpx.Response(
            200,
            json={
                "prompt_eval_count": 7500,
                "done_reason": "stop",
                "response": json.dumps({"findings": [], "relevance": "Aucun constat pertinent."}),
            },
        )

    client = httpx.Client
    monkeypatch.setattr(
        synthesis.httpx,
        "Client",
        lambda **kw: client(
            transport=httpx.MockTransport(transport),
            **kw,
        ),
    )
    result = synthesis.Generator(RagSettings())._generate("Read all evidence", {}, Notes)
    assert result.findings == []
    assert contexts == [8192, 16384]


def test_unsupported_prescriptive_numbers_and_unrelated_interventions_are_rejected():
    sources = {"D1": "Schemes aimed at restoring hedgerow biodiversity should conserve hedges."}
    valid = Actions(actions=[action()])
    validate_actions(valid, sources)
    monitored = Actions(
        actions=[
            {
                **action(),
                "priority": "monitoring",
                "monitoring": "Observer pendant 6 mois.",
            }
        ]
    )
    validate_actions(monitored, sources)
    assert "6" not in monitored.actions[0].monitoring
    assert "diagnostic local" in monitored.actions[0].monitoring
    assert monitored.actions[0].priority == "design"
    invalid = Actions(actions=[{**action(), "conditions": "Conserver une largeur de 50 m."}])
    with pytest.raises(ValueError, match="Prescription chiffrée"):
        validate_actions(invalid, sources)
    unrelated = Actions(
        actions=[
            {
                **action(),
                "action": "Créer un refuge avec une structure en bois et une couche de fougère.",
            }
        ]
    )
    with pytest.raises(ValueError, match="appui thématique"):
        validate_actions(unrelated, sources)


def test_report_quantities_require_matching_source_units():
    page = Page(
        title="Aménagement du terrain",
        paragraphs=[
            Paragraph(
                text="Prévoir une bande de 30 m sur le terrain avant tout aménagement.",
                citations=["D1"],
            )
            for _ in range(3)
        ],
    )
    with pytest.raises(ValueError, match="Distance"):
        validate_page(page, {"D1": "The study observed 30 nests."}, {"area_m2": 2500})
