"""Portable, deterministic report formatting without ML dependencies."""

import json
from typing import Any


def markdown(result: dict[str, Any]) -> str:
    # All user/publication text is emitted as plain quoted text, not interpreted instructions.
    def quote(text: Any) -> str:
        return "\n".join("> " + line for line in str(text).splitlines())

    lines = [
        "# Rapport écologique BioSentinelle — extraits sourcés",
        "",
        quote(result["question"]),
        "",
        result["message"],
        "",
        "## Faits observés et validés",
        "",
    ]
    for observation in result["observed_facts"]:
        lines.append(quote(json.dumps(observation, ensure_ascii=False, default=str)))
    if not result["observed_facts"]:
        lines.append("Aucune observation humaine validée jointe.")
    lines += ["", "## Extraits des publications", ""]
    for hit in result["hits"]:
        lines += [
            f"### [{hit['citation']}]",
            quote(hit["title"]),
            quote(
                f"DOI : {hit['doi'] or 'non renseigné'} ; page : {hit['page']} "
                f"({hit['page_kind']}) ; fragment : {hit['chunk_id']}"
            ),
            quote(hit["text"]),
            quote(f"Original : {hit['original_url']}"),
            quote(f"Source : {hit['source_url']} ; licence : {hit['license']}"),
            quote(f"SHA256 original : {hit['asset_sha256']}"),
            quote(json.dumps(hit["provenance"], ensure_ascii=False)),
            "",
        ]
    lines += [
        "## Recommandations inférées",
        "",
        "Aucune génération LLM à cette étape.",
        "",
        "## Limites et traçabilité",
        "",
        *[quote(c) for c in result["cautions"]],
        quote(
            f"Embeddings : {result['embedding_version']} ; rapport : "
            f"{result['report_version']} ; créé : {result['created_at']}"
        ),
        quote(json.dumps(result["filters"], ensure_ascii=False)),
    ]
    return "\n\n".join(lines) + "\n"
