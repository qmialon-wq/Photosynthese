"""Fast, bounded extractive screening. Every chunk is scanned; no LLM is called.

This is a lexical shortlist, not a scientific review or an entailment classifier.
Quotes remain exact source spans; adverse results and limitations get a reserved slot.
"""

import hashlib
import re

from shared.rag.grounding import SUPPORT

VERSION = "lexical-diverse-v1"
THEMES = [re.compile(pattern, re.I) for _, _, pattern in SUPPORT]
MANAGEMENT = re.compile(
    r"recommend|conserv|restor|manag|preserv|retain|mitigat|protect|"
    r"précon|restaur|gestion|rédui|éviter|limiter",
    re.I,
)
CAUTION = re.compile(
    r"however|nevertheless|not significant|did not|no evidence|negative|adverse|"
    r"uncertain|limitation|trade.off|caution|cannot|insufficient|"
    r"néanmoins|incertain|pas signific|risqu|négatif|limite",
    re.I,
)
SETTING = re.compile(
    r"urban|agricultur|farmland|landscape|habitat|forest|arable|rural|"
    r"paysag|cultures?|milieu|biodivers",
    re.I,
)


def spans(text, limit=450):
    """Split on sentence/paragraph boundaries, never rephrase or join disjoint spans."""
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])|\n\s*\n", text):
        while sentence.strip():
            sentence = sentence.strip()
            end = min(limit, len(sentence))
            if end < len(sentence):
                boundary = sentence.rfind(" ", 0, end)
                if boundary > 30:
                    end = boundary
            yield sentence[:end]
            sentence = sentence[end:]


def screen(document, rows, log):
    best, seen, read = [], set(), 0
    digest = hashlib.sha256(VERSION.encode())
    for row in rows:
        read += 1
        digest.update(row["id"].encode())
        digest.update(row["text"].encode())
        for quote in spans(row["text"]):
            normalized = " ".join(quote.lower().split())
            if len(quote) < 35 or normalized in seen:
                continue
            seen.add(normalized)
            themes = sum(bool(pattern.search(quote)) for pattern in THEMES)
            caution = bool(CAUTION.search(quote))
            management = bool(MANAGEMENT.search(quote))
            if not themes and not (caution and SETTING.search(quote)):
                continue
            score = themes * 4 + management * 5 + caution * 3 + bool(SETTING.search(quote))
            best.append((score, caution, management, row, quote))
            # Keep a bounded pool, with a separate chance for adverse/limiting passages.
            if len(best) > 40:
                ranked = sorted(best, key=lambda candidate: candidate[0], reverse=True)
                best = ranked[:20] + [c for c in ranked[20:] if c[1]][:10]
    if read != document["chunk_count"]:
        raise ValueError("Le corpus a changé pendant le repérage ; relancer le dossier")
    ranked = sorted(best, key=lambda candidate: candidate[0], reverse=True)
    selected = ranked[:1]
    if selected:
        others = [c for c in ranked[1:] if c[4] != selected[0][4]]
        # Preserve an opposite/limiting passage even if it scores below generic advice.
        diverse = [c for c in others if c[1] != selected[0][1]]
        selected += (diverse or others)[:1]
    findings = []
    for _, caution, management, row, quote in selected:
        findings.append(
            {
                "chunk_id": row["id"],
                "quote": quote,
                "finding": quote,
                "role": "limitation" if caution else "recommendation" if management else "context",
                "direction": "uncertain",
                "limits": (
                    "Extrait repéré lexicalement ; rôle indicatif, "
                    "contexte et portée à vérifier."
                ),
                "page": row["page_number"],
                "asset_id": str(row["asset_id"]),
                "asset_sha256": row["sha256"],
                "license": row["license"],
                "source_url": row["source_url"],
            }
        )
    log(
        "synthesis",
        "Repérage textuel terminé pour l’article",
        data={
            "document_id": document["id"],
            "chunks_read": read,
            "reading_method": VERSION,
            "excerpts_selected": len(findings),
        },
    )
    return {
        **document,
        "chunks_read": read,
        "findings": findings,
        "assessments": ["lexical_shortlist" if findings else "no_lexical_match"],
        "reading_method": VERSION,
        "text_snapshot": digest.hexdigest(),
    }


def shortlist(briefs, limit=8000):
    """Bound consolidation cost while preserving intervention/theme diversity.

    This ranks already validated proposals, not original documents. The complete
    document ledger and batch audit remain available independently of this shortlist.
    """
    import json

    remaining = [a for b in briefs for a in b["actions"] if a["action_type"] == "territorial"]
    selected, used_themes, used_sources, seen = [], set(), set(), set()
    size = 0
    while remaining and len(selected) < 10:

        def priority(action):
            themes = {
                i
                for i, (_, pattern, _) in enumerate(SUPPORT)
                if re.search(pattern, action["action"], re.I)
            }
            sources = set(action["citations"])
            return (len(themes - used_themes), len(sources - used_sources))

        candidate = max(remaining, key=priority)
        remaining.remove(candidate)
        text = json.dumps(candidate, ensure_ascii=False)
        normalized = " ".join(candidate["action"].lower().split())
        if normalized in seen or size + len(text) > limit:
            continue
        selected.append(candidate)
        size += len(text)
        seen.add(normalized)
        used_sources.update(candidate["citations"])
        used_themes.update(
            i
            for i, (_, pattern, _) in enumerate(SUPPORT)
            if re.search(pattern, candidate["action"], re.I)
        )
    # Actions has a maximum of six entries, so retain small intermediate groups.
    return [{"actions": selected[i : i + 3]} for i in range(0, len(selected), 3)]
