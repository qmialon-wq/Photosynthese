"""Reject unsupported quantities and clearly unrelated intervention families.

These checks complement exact citations; they do not prove ecological entailment.
"""

import re

SUPPORT = (
    (
        "végétation",
        r"haie|végét|arbr|lisièr|arbust|prair|enherb",
        r"hedg|veget|tree|shrub|woodland|grass|meadow|haie|arbr",
    ),
    ("éclairage", r"éclair|lumi|lamp", r"light|illumina|éclair|lumi"),
    (
        "continuités",
        r"clôtur|corridor|continu|passage|connect",
        r"fenc|corridor|connect|movement|passage|clôtur",
    ),
    (
        "implantation",
        r"imperméab|perméab|bâti|bâtiment|implant|stationnem|accès",
        r"impervious|soil seal|artifici|developm|building|land.use|imperméab",
    ),
    ("eau", r"mare\b|humide|eau\b", r"pond|wetland|water|riparian|humide|mare\b"),
    (
        "dérangement",
        r"travaux|nidifi|reprodu|bruit|perturb|dérang|fréquent",
        r"disturb|breed|nest|noise|recreat|touris|dérang|nidifi",
    ),
    (
        "pratiques agricoles",
        r"fauch|pesticid|herbicid|phytosanit|pâtur|labour",
        r"mow|pesticid|herbicid|graz|tillage|fauch|pâtur",
    ),
)
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?!\w)")
GROUPED_NUMBER = re.compile(
    r"(?<![\w.,])\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?(?!\w|[.,]\d)"
)
PRESCRIPTION = re.compile(
    r"\d|\b(?:deux|trois|quatre|cinq|six|dix|quinze|vingt|trente|cinquante|cent|mille)[-\s]+(?:mètres?|heures?|lux|jours?)\b",
    re.I,
)
QUANTITY = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(m²|m2|mètres?|metres?|meters?|m\b|hours?|heures?|h\b|lux|kelvins?|k\b|jours?|days?|%)",
    re.I,
)


def normalized_numbers(text):
    """Treat French thousands spaces as formatting, without joining separate numbers."""
    return GROUPED_NUMBER.sub(lambda m: re.sub(r"[ \u00a0\u202f]", "", m[0]), text)


def numbers(text):
    return {float(m[0].replace(",", ".")) for m in NUMBER.finditer(normalized_numbers(text))}


def quantities(text):
    result = set()
    for value, unit in QUANTITY.findall(normalized_numbers(text)):
        unit = unit.lower()
        if unit in ("m²", "m2"):
            unit = "m2"
        elif re.fullmatch(r"m|mètre[s]?|metre[s]?|meter[s]?", unit):
            unit = "m"
        elif unit in ("h", "hour", "hours", "heure", "heures"):
            unit = "h"
        elif unit.startswith(("jour", "day")):
            unit = "day"
        elif unit.startswith("kelvin"):
            unit = "k"
        result.add((float(value.replace(",", ".")), unit))
    return result


def validate_actions(plan, source_texts):
    for action in plan.actions:
        if action.action_type != "territorial":
            continue
        if action.priority == "monitoring":
            action.priority = "design"
        if PRESCRIPTION.search(action.monitoring):
            action.monitoring = (
                "Comparer l'état des habitats et les observations vidéo avant et après travaux, "
                "depuis les mêmes points. Définir la durée et les périodes du suivi "
                "à partir du diagnostic local."
            )
        source = "\n".join(source_texts.get(c, "") for c in action.citations)
        prescriptive = " ".join(
            (action.title, action.action, action.location, action.conditions, action.monitoring)
        )
        for citation in action.citations:
            prescriptive = re.sub(r"\b" + re.escape(citation) + r"\b", "", prescriptive)
        if PRESCRIPTION.search(prescriptive):
            raise ValueError(
                "Prescription chiffrée interdite : retirer distances, horaires, dates "
                "et seuils non validés localement, y compris en lettres."
            )
        if not numbers(action.rationale) <= numbers(source):
            raise ValueError("Résultat chiffré absent des extraits cités : retirer ce chiffre.")
        if not any(
            re.search(a, action.action, re.I) and re.search(s, source, re.I) for _, a, s in SUPPORT
        ):
            available = [name for name, _, s in SUPPORT if re.search(s, source, re.I)]
            raise ValueError(
                "Mesure sans appui thématique dans les extraits. Choisir parmi : "
                + ", ".join(available)
                + "; sinon renvoyer actions=[]."
            )


def validate_page(page, source_texts, profile):
    for paragraph in page.paragraphs:
        source = "\n".join(source_texts.get(c, "") for c in paragraph.citations)
        areas = {float(profile["area_m2"])} if profile.get("area_m2") is not None else set()
        allowed_numbers = numbers(source) | areas
        unsupported = numbers(paragraph.text) - allowed_numbers
        if unsupported:
            raise ValueError(
                "Chiffre absent du formulaire et des extraits cités : "
                f"retirer {', '.join(format(n, 'g') for n in sorted(unsupported))}."
            )
        allowed_quantities = quantities(source) | {(value, "m2") for value in areas}
        if not quantities(paragraph.text) <= allowed_quantities:
            raise ValueError(
                "Distance, horaire ou seuil sans appui exact dans les sources : "
                "retirer cette prescription."
            )
