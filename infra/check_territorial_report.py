"""Explicit local-model smoke on one real article; never writes to the production corpus."""

import json
from pathlib import Path

from shared.rag.config import RagSettings
from workers.documents import synthesis


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species", default="renards")
    parser.add_argument("--output", default="/storage/results/territorial-smoke.json")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    documents = [d for d in synthesis.corpus([args.species]) if d["chunk_count"]]
    if args.plan_only:
        from shared.parcels.report import THEMES, supporting_sentence
        from shared.rag.synthesis import Actions

        for document in sorted(documents, key=lambda d: d["chunk_count"]):
            for chunk in synthesis.chunks(document):
                for theme in THEMES:
                    quote = supporting_sentence(theme, chunk["text"])
                    if not quote:
                        continue
                    quote = chunk["text"]
                    generator = synthesis.Generator(RagSettings(generation_device=args.device))

                    def check(plan, source=quote):
                        synthesis.checked_citations(plan, {"D1"})
                        synthesis.check_action_grounding(plan, {"D1": source})

                    plan = synthesis.generate_checked(
                        generator,
                        "Propose 1 à 3 mesures d'aménagement concrètes pour une habitation "
                        "sur une prairie de 2500 m² à Caen. "
                        "Espèce ciblée non confirmée : Vulpes vulpes. "
                        "action_type=territorial exige une modification spatiale ou de gestion. "
                        "action décrit la mesure avec un verbe d'action, sans résumé d'étude. "
                        "Localisation inconnue à préciser dans location seulement. "
                        "Une phrase courte par champ, 100 mots maximum par mesure. "
                        "Aucun chiffre dans action, location, conditions ou monitoring. "
                        "Explicite les conditions de transfert, sans inventer de technique.",
                        {
                            "evidence": [
                                {"citation": "D1", "title": document["title"], "quote": quote}
                            ]
                        },
                        Actions,
                        check,
                    )
                    synthesis.checked_citations(plan, {"D1"})
                    if not any(a.action_type == "territorial" for a in plan.actions):
                        raise ValueError("Aucune mesure territoriale justifiable pour cet extrait")
                    Path(args.output).write_text(
                        json.dumps(
                            {
                                "diagnostic_only": True,
                                "document": document,
                                "quote": quote,
                                **plan.model_dump(),
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    print(
                        json.dumps(
                            {"document": document["title"], "actions": plan.model_dump()},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
        raise ValueError("Aucune préconisation explicite trouvée pour le diagnostic")
    candidates = [
        d
        for d in documents
        if any(
            term in d["title"].lower() for term in ("urban", "agricultur", "habitat", "landscape")
        )
    ] or documents
    if not candidates:
        raise ValueError("Aucun article réel extractible pour cette espèce")
    document = min(candidates, key=lambda d: d["chunk_count"])
    print(json.dumps({"diagnostic_only": True, "document": document}, default=str), flush=True)
    # Diagnostic deliberately restricted to one article; its coverage is never presented as
    # the coverage of the full production corpus or attached to a real parcel dossier.
    synthesis.corpus = lambda species: [document]
    result = synthesis.synthesize(
        {
            "area_m2": 2500,
            "land_type": "pasture",
            "project_type": "housing",
            "locality": "Caen",
            "details": "Projet de diagnostic ; aucun plan de site disponible.",
        },
        {"confirmed_species": [], "predicted_species": [{"name": args.species}], "video_count": 0},
        RagSettings(generation_device=args.device),
        lambda stage, message, **kw: print(message, kw, flush=True),
    )
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"diagnostic_only": True, **result}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    if result["status"] != "generated":
        raise ValueError("L'article du diagnostic ne contient pas assez de constats pertinents")
    print(
        json.dumps(
            {
                "status": result["status"],
                "pages": len(result["pages"]),
                "coverage": result["coverage"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
