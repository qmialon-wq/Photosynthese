"""Ciblage lexical explicite, sans inférer un bénéfice écologique ou un résultat scientifique."""

import re
import unicodedata
from typing import Any

from .schemas import Publication, Search

VERSION = "human-activities-v1"
ACTIVITIES = {
    "all": (
        "Tous les aménagements et activités",
        [
            "land use",
            "urbanization",
            "agriculture",
            "road",
            "roads",
            "artificial light",
            "recreation",
            "forest management",
            "aménagement",
            "anthropogenic noise",
        ],
    ),
    "lighting": ("Éclairage et pollution lumineuse", ["artificial light", "lighting", "éclairage"]),
    "transport": (
        "Routes, transports et passages à faune",
        ["road", "roads", "traffic", "wildlife crossing", "routier"],
    ),
    "agriculture": (
        "Agriculture, haies et bocage",
        ["agriculture", "farmland", "hedgerow", "bocage"],
    ),
    "urban": (
        "Urbanisation et aménagement du territoire",
        ["urbanization", "land use", "urban planning", "aménagement"],
    ),
    "recreation": (
        "Loisirs, tourisme et fréquentation",
        ["recreation", "tourism", "hiking", "tourisme"],
    ),
    "forestry": (
        "Gestion et exploitation forestières",
        ["forest management", "forestry", "logging", "sylviculture"],
    ),
    "noise": ("Bruit et nuisances sonores", ["anthropogenic noise", "noise pollution", "bruit"]),
}
ACTIVITY_WORDS = {
    "lighting": [
        "artificial light*",
        "light pollution",
        "lighting",
        "éclair*",
        "pollution lumineuse",
    ],
    "transport": [
        "road*",
        "highway*",
        "traffic",
        "railway*",
        "wildlife crossing*",
        "route*",
        "routier*",
        "ferroviaire*",
        "écopont*",
        "passage* à faune",
    ],
    "agriculture": [
        "agricultur*",
        "farming",
        "farmland",
        "hedgerow*",
        "pesticide*",
        "crop*",
        "bocage",
        "haie*",
    ],
    "urban": ["urban*", "land use", "land-use", "development", "construction", "aménagement*"],
    "recreation": [
        "recreation*",
        "tourism",
        "hiking",
        "dog walking",
        "trail*",
        "loisir*",
        "tourisme",
        "randonnée*",
        "fréquentation",
    ],
    "forestry": [
        "forest management",
        "forestry",
        "logging",
        "sylviculture",
        "exploitation forestière",
    ],
    "noise": ["noise", "acoustic disturbance", "nuisance* sonore*", "bruit*"],
}
EFFECT_WORDS = [
    "mitigat*",
    "conservation",
    "management",
    "design",
    "planning",
    "restoration",
    "connectivity",
    "corridor*",
    "impact*",
    "effect*",
    "disturb*",
    "avoid*",
    "reduc*",
    "mortalit*",
    "behavio*",
    "activity",
    "survival",
    "habitat use",
    "population*",
    "abundance",
    "préserv*",
    "protection",
    "effet*",
    "dérangement*",
    "activité*",
    "restauration",
    "rédu*",
    "évit*",
    "comportement*",
    "survie",
    "abondance",
    "fragmentation",
    "connectivité",
]
EFFECT_QUERY = [
    "mitigation",
    "conservation",
    "disturbance",
    "impact",
    "effects",
    "connectivity",
    "préservation",
    "effets",
    "réduction",
]


def profiles() -> dict[str, Any]:
    return {
        "version": VERSION,
        "activities": [{"value": key, "label": label} for key, (label, _) in ACTIVITIES.items()],
    }


def query_groups(search: Search) -> list[list[str]]:
    if search.focus == "general":
        return []
    return [ACTIVITIES[search.activity][1], EFFECT_QUERY]


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )


def matches(text: str, words: list[str]) -> list[str]:
    return [
        word
        for word in words
        if re.search(
            r"(?<!\w)" + re.escape(normalize(word)).replace(r"\*", r"\w*") + r"(?!\w)", text
        )
    ]


def screen(publication: Publication, search: Search) -> dict[str, Any]:
    text = normalize(publication.title + " " + (publication.abstract or ""))
    words = (
        list(dict.fromkeys(w for values in ACTIVITY_WORDS.values() for w in values))
        if search.activity == "all"
        else ACTIVITY_WORDS[search.activity]
    )
    activity, effects = matches(text, words), matches(text, EFFECT_WORDS)
    return {
        "version": VERSION,
        "focus": search.focus,
        "activity": search.activity,
        "scope": "title_and_abstract",
        "candidate": bool(activity and effects),
        "activity_terms": activity,
        "effect_terms": effects,
    }
