"""Conservative design suggestions anchored to explicit recommendations in source sentences."""

import re
from dataclasses import dataclass
from html import escape
from typing import Any


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    query: str
    intervention: str
    action: str


THEMES = (
    Theme(
        "vegetation",
        "Végétation et terrain vert",
        "preserve vegetation hedgerows trees",
        r"\b(?:maintain|retain|preserv|restor|plant|conserv|préserv|restaur)\w*.{0,100}"
        r"\b(?:hedgerows?|hedges?|vegetation|trees?|haies?|arbres?|végétation)\b",
        "Étudier la conservation des arbres et des haies existants, et leur restauration "
        "dans les espaces compatibles avec votre activité.",
    ),
    Theme(
        "connections",
        "Déplacements des animaux",
        "wildlife corridors habitat connectivity",
        r"\b(?:maintain|preserv|creat|restor|conserv|préserv|cré|restaur)\w*.{0,100}"
        r"\b(?:corridors?|habitat connectivity|ecological connectivity|connectivité écologique|"
        r"wildlife passage|passage.{0,20}faune)\b",
        "Étudier des continuités végétales et des passages adaptés aux espèces confirmées, "
        "en vérifiant leur compatibilité avec les clôtures et les usages du site.",
    ),
    Theme(
        "lighting",
        "Éclairage",
        "reduce artificial lighting wildlife impacts",
        r"\b(?:reduc|limit|avoid|dim|rédu|évit)\w*.{0,80}(?:light|éclair|lumi)",
        "Étudier un éclairage limité aux lieux et aux périodes nécessaires à l'activité, "
        "avec des zones préservées de l'éclairage.",
    ),
    Theme(
        "soil",
        "Implantation et perméabilité",
        "reduce impervious surface soil sealing habitat",
        r"\b(?:reduc|limit|avoid|rédu|évit)\w*.{0,80}"
        r"(?:impervious|soil seal|artificial(?:ised|ized)?\s+(?:surfaces?|land)|"
        r"artificialisation|imperméab)",
        "Comparer des implantations regroupant les surfaces bâties et les accès, "
        "et examiner les solutions perméables compatibles avec les usages.",
    ),
    Theme(
        "water",
        "Eau et microhabitats",
        "preserve ponds wetlands wildlife habitat",
        r"\b(?:retain|preserv|restor|creat|maintain|conserv|préserv|restaur|cré)\w*.{0,80}"
        r"\b(?:ponds?|wetlands?|mares?|zones?\s+humides?)\b",
        "Examiner la préservation des zones humides et points d'eau existants avant "
        "d'envisager de nouveaux aménagements, selon le sol et les usages du site.",
    ),
    Theme(
        "timing",
        "Calendrier du projet",
        "avoid disturbance breeding nesting habitat works",
        r"\b(?:avoid|limit|évit)\w*.{0,80}(?:breeding|nesting|reproduct|nidifica)",
        "Étudier un calendrier des travaux tenant compte des périodes sensibles "
        "des espèces confirmées ; les dates locales restent à déterminer.",
    ),
)
DIRECTIVE = re.compile(
    r"\b(?:recommend\w*|should|advis\w*|recommand\w*|préconis\w*|devrai\w*)\b", re.I
)
NEGATIVE = re.compile(
    r"\b(?:not|no|never|cannot|can't|ineffective|avoid(?:ed|ing)?|pas|aucun\w*|inefficace\w*)\b",
    re.I,
)
CONDITIONAL = re.compile(
    r"\b(?:unless|except|however|although|whereas|only if|sauf|cependant)\b", re.I
)


def supporting_sentence(theme: Theme, text: str) -> str | None:
    """A cautious lexical gate, not a claim of scientific entailment or a substitute for review."""
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if not 30 <= len(sentence) <= 900 or not DIRECTIVE.search(sentence):
            continue
        # 'avoid lighting' is itself the proposed intervention, not a negation of it.
        checked = re.sub(
            r"\bavoid\b(?=\s+(?:artificial\s+)?(?:lighting|light|disturbance))",
            "",
            sentence,
            flags=re.I,
        )
        if NEGATIVE.search(checked) or CONDITIONAL.search(sentence):
            continue
        if re.search(theme.intervention, sentence, re.I):
            return sentence.strip()
    return None


def suggestions(theme: Theme, hits: list[dict[str, Any]], confirmed: bool) -> dict[str, Any]:
    for hit in hits:
        quote = supporting_sentence(theme, hit["text"])
        if quote:
            return {
                "theme": theme.key,
                "title": theme.title,
                "status": "supported_direction",
                "action": theme.action,
                "citation": hit["citation"],
                "evidence_quote": quote,
                "qualification": "Piste de conception inférée à vérifier sur le terrain."
                if confirmed
                else "Piste générale ou conditionnelle : aucune présence "
                "d'espèce confirmée n'est utilisée.",
                "species_conditional": not confirmed,
            }
    return {
        "theme": theme.key,
        "title": theme.title,
        "status": "insufficient_evidence",
        "action": "Les sources retenues ne permettent pas de proposer une mesure spécifique "
        "pour ce thème. Une expertise ou des sources complémentaires sont nécessaires.",
        "citation": None,
        "evidence_quote": None,
        "species_conditional": not confirmed,
    }


def planning_questions(profile: dict[str, Any]) -> list[str]:
    # These are questions for the design process, not empirical claims from publications.
    project = {
        "housing": "Où implanter l'habitation, les accès et les stationnements en préservant "
        "les éléments existants identifiés sur le plan ?",
        "crops": "Quelles zones de production et quelles bordures conserver pour concilier "
        "les circulations agricoles et les habitats identifiés ?",
        "livestock": "Comment concilier passages d'animaux sauvages, sécurité des animaux "
        "d'élevage et fonction des clôtures ?",
        "park": "Quels espaces réserver aux usages du parc, aux cheminements et aux "
        "secteurs moins fréquentés ?",
        "other": "Quels espaces sont indispensables à votre activité et quels éléments "
        "existants peuvent être conservés ?",
    }
    land = {
        "woodland": "Quels arbres, lisières et habitats forestiers faut-il cartographier "
        "avant de comparer les variantes du projet ?",
        "pasture": "Où se trouvent les haies, les prairies, les points d'eau "
        "et les accès existants ?",
        "fallow": "Quels habitats et usages actuels de la friche faut-il inventorier "
        "avant de la transformer ?",
        "buildable": "Quels éléments naturels sont présents sur le terrain, indépendamment "
        "de sa qualification constructible déclarée ?",
        "artificial": "Quelles surfaces et quels usages existants faut-il relever pour "
        "examiner les possibilités de végétalisation et de perméabilité ?",
    }
    return [project[profile["project_type"]], land[profile["land_type"]]]


def render(data: dict[str, Any], *, markdown: bool = False) -> str:
    if data.get("territorial_report", {}).get("status") == "generated":
        return render_territorial(data, markdown=markdown)

    def heading(title: str, level: int = 2) -> str:
        return f"{'#' * level} {title}" if markdown else f"{title}\n{'=' * len(title)}"

    lines = [
        heading("Dossier biodiversité de votre parcelle", 1),
        f"Version : {data['version']} — établi le {data['created_at']}",
        heading("1. Votre parcelle et votre projet"),
        f"Surface : {data['profile']['area_m2']:g} m²",
        f"Type : {data['land_label']} — Projet : {data['project_label']}",
        f"Commune / secteur : {data['profile'].get('locality') or 'Non renseigné'}",
        data["profile"].get("details", ""),
        heading("2. Ce que montrent les vidéos"),
        f"Corpus : {data.get('video_count', 1)} vidéo(s) distincte(s). "
        "Des détections répétées ne sont pas un décompte d'individus.",
        data["observation_summary"],
    ]
    for row in data["confirmed_species"]:
        lines.append(f"- {row['display_name']} : présence confirmée par annotation humaine.")
    for row in data["predicted_species"]:
        lines.append(
            f"- {row['display_name']} : hypothèse automatique, confiance {row['score']:.1%}. "
            "Présence à confirmer."
        )
    lines.extend([heading("3. Pistes d'aménagement compatibles avec votre activité")])
    for card in data["recommendations"]:
        lines += [heading(card["title"], 3), card["action"]]
        if card.get("citation"):
            lines += [
                card["qualification"],
                f"Source [{card['citation']}] : « {card['evidence_quote']} »",
            ]
    lines += [
        heading("4. Quelle part de terrain vert ?"),
        data["green_space"]["message"],
        heading("5. Points à vérifier et prochaines étapes"),
        *data["planning_questions"],
        *data["next_steps"],
        *data["limitations"],
        heading("6. Sources utilisées et traçabilité"),
    ]
    if not data["sources"]:
        lines.append(
            "Aucune source validée suffisamment pertinente : aucune mesure spécifique affirmée."
        )
    for source in data["sources"]:
        lines += [
            f"[{source['citation']}] {source['title']}",
            f"DOI : {source.get('doi') or 'Non renseigné'} — page {source['page']}",
            f"Passage : {source['chunk_id']} — langue : {source['language']}",
            f"Original : {source['original_url']}",
            f"Provenance : {source['source_url']} — licence : {source['license']}",
            f"Empreinte du document : {source['asset_sha256']}",
        ]
    lines += [heading("7. Vidéos et versions des données")]
    for video in data.get("videos", []):
        lines += [
            f"- {video['filename']} : {video['annotated_video_url']}",
            f"  Analyse : {video['analysis_id']} — original : {video['sha256']}",
            f"  Empreinte du rapport : {video['report_sha256']}",
        ]
    if not data.get("videos"):
        lines.append(f"Vidéo annotée : {data['annotated_video_url']}")
    lines += [
        f"Formulaire : révision {data['profile_revision']}",
        f"Empreinte du contexte : {data['snapshot_sha256']}",
        "Ce dossier est un instantané. Après une correction d'espèce ou du projet, "
        "actualiser le dossier pour intégrer les nouvelles informations.",
    ]
    return "\n\n".join(str(line) for line in lines if line) + "\n"


def render_territorial(data: dict[str, Any], *, markdown: bool = False) -> str:
    report = data["territorial_report"]
    lines = [
        "# Dossier territorial — recommandations d'aménagement",
        "",
        f"Votre parcelle : {data['profile']['area_m2']:g} m² — "
        f"{data['land_label']} — {data['project_label']}",
        f"Localité : {data['profile'].get('locality') or 'Non renseignée'}",
        f"Corpus examiné : {report['coverage']['documents_read']} / "
        f"{report['coverage']['documents_total']} documents.",
        "Les recommandations sont des propositions de conception sourcées, à vérifier sur le site.",
    ]
    if report["coverage"].get("reading_method"):
        lines.append(report["coverage"]["reading_method"])
    for i, page in enumerate(report["pages"], 1):
        lines.extend([f"## Page {i}/4 — {page['title']}"])
        for paragraph in page["paragraphs"]:
            lines.append(
                paragraph["text"] + " " + " ".join(f"[{c}]" for c in paragraph["citations"])
            )
    lines.append("## Fiches de mise en œuvre")
    for action in report["actions"]:
        lines.extend(
            [
                f"### {action['title']}",
                action["action"],
                f"Où : {action['location']}",
                f"Justification : {action['rationale']}",
                f"Conditions : {action['conditions']}",
                "Priorité : "
                + {
                    "before_project": "Avant le projet",
                    "design": "Conception",
                    "works": "Travaux",
                    "monitoring": "Suivi",
                }[action["priority"]],
                f"Suivi : {action['monitoring']}",
                "Références : " + ", ".join(action["citations"]),
            ]
        )
    lines.append("## Annexe — ensemble du corpus examiné")
    for doc in report["ledger"]:
        lines.append(
            f"[{doc['citation']}] {doc['title']} — DOI : {doc['doi'] or 'non renseigné'} — "
            f"{doc['chunks_read']} passages lus — "
            f"pertinence : {doc['relevance']} / qualité : {doc['quality']}"
        )
        if doc.get("authors"):
            lines.append("Auteurs : " + ", ".join(doc["authors"]))
        lines.extend(doc.get("assessments", []))
        for finding in doc["findings"]:
            lines.extend(
                [
                    finding["finding"],
                    f"Limites : {finding['limits']}",
                    f"Extrait original, page {finding['page']} ({finding['chunk_id']}) : "
                    f"« {finding['quote']} »",
                ]
            )
    lines.extend(["## Limites", *data["limitations"]])
    text = "\n\n".join(lines) + "\n"
    return text if markdown else re.sub(r"(?m)^#{1,3} ", "", text)


def printable_html(data: dict[str, Any]) -> str:
    report = data.get("territorial_report", {})
    if report.get("status") != "generated":
        raise ValueError("Aucun rapport territorial rédigé pour cet instantané")
    pages = []
    coverage = report["coverage"]
    for i, page in enumerate(report["pages"], 1):
        compact = sum(len(p["text"]) for p in page["paragraphs"]) > 3000
        page_class = "page compact" if compact else "page"
        paragraphs = "".join(
            f"<p>{escape(p['text'])} <span class='citations'>"
            + escape(" ".join(f"[{c}]" for c in p["citations"]))
            + "</span></p>"
            for p in page["paragraphs"]
        )
        pages.append(f"""<section class="{page_class}">
          <header>BIOSENTINELLE · DOSSIER TERRITORIAL</header>
          <h1>{escape(page["title"])}</h1>
          <div class="context">
          {escape(data["profile"].get("locality") or "Localité non renseignée")} ·
          {data["profile"]["area_m2"]:g} m² · {escape(data["land_label"])} ·
          {escape(data["project_label"])}</div>
          {paragraphs}<footer>{coverage["documents_read"]}/{coverage["documents_total"]}
          documents examinés ·
          {coverage.get("documents_pending_review", 0)} en attente de validation · Page {i}/4<br>
          Références, extraits et fiches de mise en œuvre : annexe complète TXT/JSON du dossier.
          Recommandations à vérifier sur le site.</footer></section>""")
    return (
        """<!doctype html><html lang="fr"><meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Dossier territorial BioSentinelle</title><style>
      @page {size:A4;margin:0} * {box-sizing:border-box}
      body {margin:0;background:#ecefe9;color:#19352c;font:10pt/1.35 Georgia,serif}
      .page {position:relative;width:210mm;min-height:297mm;padding:20mm 20mm 28mm;
      margin:8mm auto;background:white;break-after:page}
      .page:last-child {break-after:auto} header {font:9pt Arial,sans-serif;letter-spacing:2px}
      h1 {font: bold 21pt/1.2 Georgia,serif;margin:5mm 0 4mm}
      .context {font:9pt Arial,sans-serif;padding-bottom:3mm;border-bottom:1px solid #b4c4b8}
      p {margin:4mm 0;text-align:left;orphans:3;widows:3} .citations {font:9pt Arial,sans-serif}
      .compact {font-size:9.5pt;line-height:1.3} .compact p {margin:3mm 0}
      footer {position:absolute;bottom:12mm;left:20mm;right:20mm;font:8pt/1.4 Arial,sans-serif;
      border-top:1px solid #b4c4b8;padding-top:3mm}
      @media print {body {background:white} .page {margin:0;height:297mm;min-height:0}}
      @media screen and (max-width:800px) {.page {width:auto;margin:0;padding:20px 20px 110px}}
      </style><body>"""
        + "".join(pages)
        + "</body></html>"
    )
