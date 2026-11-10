"""Conditional design options. Context supports reflection, never presumed local efficacy."""

import re
from typing import Any

from shared.parcels.schemas import INTERVENTIONS

# General design references, checked on 2026-11-10. They are not local scientific evidence.
REFERENCES = {
    "lighting": {
        "id": "design:lighting",
        "title": "Ministère — Trame noire et éclairage",
        "url": "https://www.ecologie.gouv.fr/politiques-publiques/trame-verte-bleue",
    },
    "fencing": {
        "id": "design:fencing",
        "title": "OFB — Clôtures : impacts sur la faune",
        "url": "https://patbiodiv.ofb.fr/index.php/fiche-methodologique/"
        "amenagements-terrestres/clotures-impacts-faune-887",
    },
    "soil": {
        "id": "design:soil",
        "title": "Cerema — Désimperméabilisation des sols",
        "url": "https://www.cerema.fr/system/files/documents/2022/11/"
        "2022_plaquette_desimpermeabilisation.pdf",
    },
}

# No dimensions, species-specific equipment or ecological gain is inferred from a declaration.
CATALOGUE = {
    "fencing": [
        (
            "reroute",
            "avoid",
            "Modifier le tracé de la clôture",
            "Si des secteurs à préserver sont identifiés, comparer un tracé qui les contourne.",
            "Le tracé et les accès seraient déplacés par rapport au plan initial à définir.",
            [
                "Disposer du tracé initial et repérer les éléments réellement présents.",
                "Vérifier limites foncières, accès, usages et sécurité.",
            ],
            "fencing",
        ),
        (
            "smaller_perimeter",
            "reduce",
            "Limiter le périmètre clôturé",
            "Si la fermeture intégrale n’est pas nécessaire aux usages, étudier la clôture "
            "des seuls secteurs qui l’exigent.",
            "Le linéaire serait réduit et certains secteurs resteraient ouverts, "
            "selon les besoins.",
            [
                "Identifier les zones nécessitant effectivement une fermeture.",
                "Vérifier sécurité, surveillance et éventuelle contention d’animaux.",
            ],
            "fencing",
        ),
        (
            "wildlife_design",
            "reduce",
            "Examiner une conception adaptée à la faune",
            "Si des déplacements de faune sur l’emprise sont confirmés et les usages compatibles, "
            "étudier avec un spécialiste une conception permettant les passages pertinents.",
            "Le type de clôture ou certains segments seraient adaptés après étude des usages "
            "et des espèces concernées.",
            [
                "Observer les déplacements effectifs et préciser les espèces concernées.",
                "Évaluer sécurité, risques de piégeage et compatibilité avec les usages.",
                "Faire définir la conception adaptée ; aucune dimension n’est prescrite ici.",
            ],
            "fencing",
        ),
    ],
    "outdoor_lighting": [
        (
            "omit_points",
            "avoid",
            "Éviter certains points lumineux",
            "Si certains usages peuvent fonctionner sans éclairage, comparer une variante "
            "supprimant les points lumineux correspondants.",
            "Le nombre ou l’implantation des points lumineux serait revu ; certains secteurs "
            "ne seraient pas éclairés.",
            [
                "Localiser les points envisagés et justifier le besoin de chacun.",
                "Vérifier les conditions de déplacement, d’accessibilité et de sécurité.",
            ],
            "lighting",
        ),
        (
            "shorter_operation",
            "reduce",
            "Réduire la durée de fonctionnement",
            "Si les besoins ne couvrent pas toute la nuit, comparer des horaires plus courts "
            "ou un fonctionnement déclenché par l’usage.",
            "Le programme de fonctionnement serait limité aux périodes nécessaires plutôt "
            "qu’aux plages initialement envisagées.",
            [
                "Connaître les horaires réels d’usage et les contraintes de sécurité.",
                "Examiner la compatibilité d’une programmation ou d’une détection de présence.",
            ],
            "lighting",
        ),
        (
            "orientation",
            "reduce",
            "Adapter l’orientation de l’éclairage",
            "Si l’éclairage reste nécessaire, étudier une orientation ciblée sur les surfaces "
            "utiles, en évitant d’éclairer les éléments voisins à préserver s’ils sont identifiés.",
            "La position ou l’orientation des luminaires serait modifiée ; le flux serait "
            "ciblé sur les usages retenus.",
            [
                "Réaliser un plan d’éclairage et identifier les éléments voisins "
                "réellement présents.",
                "Faire vérifier visibilité, sécurité et choix techniques "
                "par une personne compétente.",
            ],
            "lighting",
        ),
    ],
    "vegetation_removal": [
        (
            "retain_layout",
            "avoid",
            "Implanter le projet en préservant la végétation présente",
            "Si des arbres ou des haies sont effectivement présents, comparer une implantation "
            "qui les conserve avec leurs espaces de fonctionnement à déterminer.",
            "La position des constructions, cheminements ou accès serait ajustée pour "
            "conserver les éléments identifiés.",
            [
                "Inventorier la végétation et la reporter sur le plan du projet.",
                "Faire examiner état des arbres, espace racinaire, usages et sécurité.",
            ],
            None,
        ),
        (
            "selective_removal",
            "reduce",
            "Réduire l’emprise de suppression de végétation",
            "Si une suppression reste nécessaire, comparer une emprise limitée aux éléments "
            "strictement incompatibles avec les usages après examen sur site.",
            "L’emprise de suppression serait réduite ; les éléments conservables seraient "
            "identifiés et intégrés à l’organisation du chantier.",
            [
                "Délimiter l’emprise initiale et les éléments à conserver ou à examiner.",
                "Vérifier les enjeux écologiques et les contraintes techniques "
                "avant toute intervention.",
            ],
            None,
        ),
    ],
    "earthworks": [
        (
            "different_layout",
            "avoid",
            "Comparer une implantation différente",
            "Si des enjeux sont confirmés sur l’emprise initiale, comparer sur plan une "
            "implantation qui évite les secteurs concernés.",
            "L’implantation et éventuellement les accès seraient déplacés ; le plan de "
            "terrassement devrait être recalculé.",
            [
                "Disposer du plan initial, de la topographie et des enjeux réellement localisés.",
                "Vérifier faisabilité géotechnique, accès et contraintes du projet.",
            ],
            None,
        ),
        (
            "smaller_footprint",
            "reduce",
            "Réduire l’emprise des terrassements",
            "Si les besoins techniques le permettent, comparer une organisation limitant "
            "les surfaces remaniées et les emprises temporaires de chantier.",
            "La zone de travaux, les circulations ou les stockages temporaires seraient "
            "resserrés ; les volumes resteraient à calculer.",
            [
                "Distinguer emprises définitives, circulations et stockages temporaires.",
                "Faire vérifier stabilité, gestion des terres et faisabilité du chantier.",
            ],
            None,
        ),
    ],
    "soil_sealing": [
        (
            "smaller_sealed_area",
            "avoid",
            "Éviter des surfaces imperméabilisées non indispensables",
            "Si les usages le permettent, comparer un plan réduisant les surfaces revêtues "
            "et regroupant certains accès ou espaces de circulation.",
            "La surface à imperméabiliser serait réduite ; les espaces laissés non revêtus "
            "et les usages associés seraient redéfinis.",
            [
                "Mesurer les surfaces prévues et préciser les usages, charges et accès requis.",
                "Vérifier circulation, accessibilité, sécurité et entretien.",
            ],
            "soil",
        ),
        (
            "permeable_surfaces",
            "reduce",
            "Examiner des revêtements perméables compatibles avec les usages",
            "Si le sol, la gestion de l’eau et les usages sont compatibles, comparer "
            "certains revêtements prévus avec des solutions perméables.",
            "La structure de certaines surfaces, leur drainage et leur entretien seraient "
            "modifiés après étude technique.",
            [
                "Étudier sol, sous-sol, infiltration et éventuelles pollutions.",
                "Vérifier charges, accessibilité, gestion de l’eau et entretien.",
                "Faire examiner la solution technique ; sa pertinence sur site n’est pas établie.",
            ],
            "soil",
        ),
    ],
}


def qualified_for(
    source: dict, code: str, alternative_id: str, category: str, observed_species: set[str]
) -> bool:
    """A lexical hit, general guide or generic reviewed theme cannot qualify a specific option."""
    return bool(
        source.get("evidence_type") == "scientific"
        and source.get("applicability") == "reviewed"
        and source.get("project_action") == code
        and source.get("category") == category
        and isinstance(source.get("design_alternative_ids"), list)
        and alternative_id in source["design_alternative_ids"]
        and isinstance(source.get("quote"), str)
        and source["quote"].strip()
        and isinstance(source.get("sha256"), str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", source["sha256"])
        and isinstance(source.get("page"), int)
        and not isinstance(source["page"], bool)
        and source["page"] > 0
        and set(source.get("species", [])) & observed_species
    )


def contextual_fact_ids(code: str, facts: list[dict], sources: list[dict]) -> list[str]:
    by_id = {s["id"]: s for s in sources}
    selected = []
    for fact in facts:
        refs = [by_id.get(ref, {}) for ref in fact.get("source_refs", [])]
        if code == "fencing":
            relevant = fact["kind"] == "human_observation" and any(
                s.get("species") in {"chevreuil", "sanglier", "martres", "renards", "blaireaux"}
                for s in refs
            )
        elif code in ("earthworks", "soil_sealing"):
            relevant = fact["kind"] == "map_result" and any(
                s.get("status") == "success" and s.get("nature") in ("inventoried", "predisposed")
                and s.get("provider") == "dreal"
                for s in refs
            )
        else:
            relevant = False
        if relevant:
            selected.append(fact["id"])
    return selected


def propose(profile: dict, facts: list[dict], sources: list[dict]) -> list[dict[str, Any]]:
    proposals = []
    observed_species = {s["species"] for s in sources if s.get("sample_id") and s.get("species")}
    for code in dict.fromkeys(profile.get("interventions", [])):
        context_refs = contextual_fact_ids(code, facts, sources)
        evidence_refs = [f"project:{code}", *context_refs]
        related_sources = {s for f in facts if f["id"] in context_refs for s in f["source_refs"]}
        related_sources |= {s["id"] for s in sources if s.get("project_action") == code}
        alternatives = []
        for key, category, title, proposal, change, conditions, reference in CATALOGUE[code]:
            alternative_id = f"{code}:{key}"
            source_refs = set(related_sources) | {"erc-framework"}
            if reference:
                ref = {
                    **REFERENCES[reference],
                    "role": "general_design_reference",
                    "accessed_at": "2026-11-10",
                    "scope": "Référence générale ; applicabilité au site non évaluée.",
                }
                if not any(s["id"] == ref["id"] for s in sources):
                    sources.append(ref)
                source_refs.add(ref["id"])
            qualified = [
                s
                for s in sources
                if qualified_for(s, code, alternative_id, category, observed_species)
            ]
            level = (
                "scientifically_qualified"
                if qualified
                else ("contextualized" if context_refs else "exploratory")
            )
            reason = {
                "exploratory": "Option issue de l’intervention déclarée et du répertoire de "
                "conception ; aucun enjeu local n’est établi par ces références générales.",
                "contextualized": "Des données de contexte citées motivent l’examen de cette "
                "variante. Elles ne démontrent ni son efficacité locale, ni sa faisabilité.",
                "scientifically_qualified": "Une source avec extrait et applicabilité examinée "
                "porte sur cette alternative précise. Sa mise en œuvre reste conditionnelle.",
            }[level]
            source_refs |= {s["id"] for s in qualified}
            qualified_species = {species for s in qualified for species in s.get("species", [])}
            human_sources = {
                s["id"]
                for s in sources
                if s.get("sample_id") and s.get("species") in qualified_species
            }
            option_evidence = list(
                dict.fromkeys(
                    [
                        *evidence_refs,
                        *[
                            f["id"]
                            for f in facts
                            if f["kind"] == "human_observation"
                            and human_sources.intersection(f["source_refs"])
                        ],
                    ]
                )
            )
            source_refs |= human_sources
            alternatives.append(
                {
                    "id": alternative_id,
                    "category": category,
                    "title": title,
                    "proposal": proposal,
                    "project_change": change,
                    "conditions": conditions,
                    "evidence_refs": option_evidence,
                    "source_refs": sorted(source_refs),
                    "justification": {"level": level, "reason": reason},
                    "status": "conditional_design_option",
                    "limitations": [
                        "Option de conception à comparer au projet initial ; "
                        "efficacité locale non présumée.",
                        "Les dimensions, coûts et gains éventuels ne sont pas évalués.",
                    ],
                }
            )
        proposals.append(
            {
                "project_action": code,
                "initial_intervention": INTERVENTIONS[code],
                "issue": {
                    "fencing": "Fermeture, usages et déplacements de faune à examiner.",
                    "outdoor_lighting": (
                        "Besoins d’éclairage et exposition des éléments voisins à examiner."
                    ),
                    "vegetation_removal": (
                        "Végétation effectivement présente et emprise de suppression à examiner."
                    ),
                    "earthworks": "Emprise réelle, sols et habitats concernés à examiner.",
                    "soil_sealing": (
                        "Surfaces nécessaires, usages du sol et gestion de l’eau à examiner."
                    ),
                }[code],
                "alternatives": alternatives,
            }
        )
    return proposals
