"""Deterministic ERC: verified records are never treated as ecological conclusions."""

from shared.parcels.schemas import INTERVENTIONS

RULES_VERSION = "territorial-erc-v2-design"
TERRESTRIAL = {"chevreuil", "sanglier", "martres", "renards", "blaireaux"}
LIMITATIONS = [
    "Le point interrogé ne représente ni le contour de la parcelle ni l’emprise des travaux.",
    "Une intersection IGN ne démontre ni habitat précis ni impact du projet.",
    "Une observation isolée ne démontre ni reproduction, ni abondance, ni corridor écologique.",
    "Un résultat vide ne démontre aucune absence de biodiversité ou d’enjeu.",
    "Qualification réglementaire non réalisée : aucun zonage ne vaut ici décision juridique.",
    "Les choix enregistrés sont des déclarations du projet, pas des constats écologiques.",
]
ERC_URL = (
    "https://www.ecologie.gouv.fr/politiques-publiques/"
    "eviter-reduire-compenser-impacts-lenvironnement"
)


def analyze(inputs: dict, layers: dict, revision: int, documents: list | None = None) -> dict:
    facts, sources, actions, concerns, unknowns = [], [], [], [], []
    profile = inputs.get("profile", {})
    interventions = profile.get("interventions", [])
    observations = [
        r for r in inputs.get("observations", []) if r.get("state") in ("validated", "corrected")
    ]
    for code in interventions:
        facts.append(
            {
                "id": f"project:{code}",
                "kind": "user_declaration",
                "text": f"Intervention déclarée : {INTERVENTIONS[code]}.",
                "source_refs": [],
            }
        )
    for row in observations:
        ref = f"human:{row['sample_id']}:{row['revision']}"
        facts.append(
            {
                "id": ref,
                "kind": "human_observation",
                "text": f"Identification humaine enregistrée : {row['species']} "
                f"(observation {row['sample_id']}, révision {row['revision']}).",
                "source_refs": [ref],
            }
        )
        sources.append(
            {
                "id": ref,
                "title": f"Observation humaine — {row['species']}",
                "sample_id": row["sample_id"],
                "species": row["species"],
                "revision": row["revision"],
                "validator": row.get("validator"),
                "retrieved_at": row.get("validated_at"),
            }
        )
    intersections = []
    for layer, row in layers.items():
        sources.append(
            {
                "id": f"ign:{layer}",
                "title": f"IGN Nature — {layer}",
                "url": row["source_url"],
                "retrieved_at": row["retrieved_at"],
                "sha256": row.get("sha256"),
                "status": row["status"],
            }
        )
        if row["status"] == "success":
            for feature in row["features"]:
                ref = f"ign:{layer}:{feature['source_id']}"
                facts.append(
                    {
                        "id": ref,
                        "kind": "map_result",
                        "text": f"Le point interrogé intersecte {feature['name']} ({layer}).",
                        "source_refs": [f"ign:{layer}"],
                    }
                )
                intersections.append(ref)
        elif row["status"] == "empty":
            facts.append(
                {
                    "id": f"ign:{layer}:empty",
                    "kind": "map_result",
                    "text": f"Aucun zonage renvoyé pour ce point par la couche {layer}.",
                    "source_refs": [f"ign:{layer}"],
                }
            )
        else:
            unknowns.append(
                f"Couche {layer} {row['status']} : résultat territorial inconnu. "
                f"{row.get('error', '')}"
            )
    if "interventions" not in profile:
        unknowns.append("Interventions non renseignées dans ce profil historique.")
    elif not interventions:
        unknowns.append(
            "Liste d’interventions explicitement vide ; absence de travaux non établie."
        )
    if not observations:
        unknowns.append("Aucune espèce validée humainement dans ce dossier ; présence non établie.")
    human_refs = [
        f"human:{r['sample_id']}:{r['revision']}"
        for r in observations
        if r["species"] in TERRESTRIAL
    ]
    for code in interventions or ["project_details"]:
        refs = [f"project:{code}"] if code in INTERVENTIONS else []
        missing = ["Emprise réelle, calendrier, usages et contraintes du projet à préciser."]
        if code == "fencing":
            issue = "Conception et usages de la clôture"
            text = (
                "Examiner le tracé et les besoins de fermeture. Si la faune terrestre "
                "observée utilise cette emprise, vérifier ses déplacements réels, "
                "les contraintes de sécurité et la possibilité d’une adaptation documentée."
                if human_refs
                else "Préciser le tracé, les usages et la conception de la clôture ; "
                "vérifier sur le terrain si des déplacements de faune sont concernés."
            )
            refs += human_refs
            missing += [
                "Déplacements effectifs sur l’emprise et source applicable à une adaptation."
            ]
        elif code == "outdoor_lighting":
            issue = "Nécessité, emplacement et fonctionnement de l’éclairage"
            text = (
                "Examiner la nécessité d’éclairer, les emplacements et les horaires. "
                "Documenter les sensibilités réellement présentes avant de proposer "
                "une alternative sans éclairage ou une réduction de son fonctionnement."
            )
            missing += ["Besoin d’éclairage, sensibilités locales et sources applicables."]
        elif code == "vegetation_removal":
            issue = "Éléments de végétation réellement concernés"
            text = (
                "Inventorier les éléments effectivement présents et l’emprise de suppression. "
                "Si des enjeux sont documentés, étudier leur conservation dans le projet."
            )
            missing += ["Inventaire de la végétation et enjeux étayés sur les éléments concernés."]
            refs += intersections
        elif code in ("earthworks", "soil_sealing"):
            issue = "Emprise des terrassements ou des surfaces imperméabilisées"
            text = (
                "Le point intersecte un zonage IGN : examiner l’emprise réelle et les habitats "
                "sur le terrain avant de qualifier les effets des travaux."
                if intersections
                else "Délimiter l’emprise réelle et examiner les habitats sur le terrain avant "
                "de qualifier les effets des travaux ; les couches ne suffisent pas à les exclure."
            )
            refs += intersections
            missing += ["Plan d’emprise et constat des habitats réellement présents."]
        else:
            issue = "Interventions du projet à préciser"
            text = (
                "Décrire les travaux, leur localisation et leur calendrier, y compris les "
                "autres interventions dans les précisions du projet."
            )
        source_refs = sorted(
            {ref for fact in facts if fact["id"] in refs for ref in fact["source_refs"]}
        )
        action = {
            "category": "investigate",
            "project_action": code,
            "issue": issue,
            "action": text,
            "rationale": "Vérification générale déclenchée par les entrées "
            "citées ; leur enregistrement ne démontre pas un impact écologique.",
            "evidence_refs": refs,
            "source_refs": source_refs,
            "preconditions": ["Vérification sur site et examen des usages du projet."],
            "missing_information": missing,
            "limitations": LIMITATIONS[:3],
            "evidence_status": "general_verification",
        }
        concerns.append({"project_action": code, "issue": issue, "evidence_refs": refs})
        actions.append(action)
        # A lexical hit alone is never eligible. Only an explicit, reviewed applicability
        # assessment can support a conditional measure. The optional retriever supplies none.
        applicable = [
            d
            for d in documents or []
            if d.get("applicability") == "reviewed"
            and d.get("quote")
            and d.get("project_action") == code
            and d.get("category") in ("avoid", "reduce")
            and d.get("sha256")
            and d.get("page")
            and set(d.get("species", [])) & {r["species"] for r in observations}
        ]
        for doc in applicable:
            sources.append(doc)
            actions.append(
                {
                    **action,
                    "category": doc["category"],
                    "action": f"Si les enjeux et l’applicabilité sur site sont confirmés : "
                    f"{doc['proposal']}",
                    "rationale": "Piste conditionnelle appuyée par un extrait dont "
                    "l’applicabilité a été examinée ; efficacité locale non établie.",
                    "source_refs": [*source_refs, doc["id"]],
                    "preconditions": [
                        *action["preconditions"],
                        "Confirmer l’applicabilité de la source au site.",
                    ],
                    "evidence_status": "conditional_proposal",
                }
            )
    # General references and lexical candidates remain distinct from qualified measures.
    for doc in documents or []:
        if (
            doc.get("project_action") in interventions
            and doc.get("id")
            and not any(source["id"] == doc["id"] for source in sources)
        ):
            sources.append(doc)
    sources.append(
        {
            "id": "erc-framework",
            "title": "Cadre officiel ERC",
            "url": ERC_URL,
            "role": "general_design_reference",
        }
    )
    from shared.parcels.design import propose

    design_proposals = propose(profile, facts, sources)
    return {
        "rules_version": RULES_VERSION,
        "analysis_revision": revision,
        "facts": facts,
        "project_concerns": concerns,
        "actions": actions,
        "unknowns": unknowns,
        "sources": sources,
        "design_proposals": design_proposals,
        "limitations": LIMITATIONS,
        "compensation": {"status": "not_assessed"},
    }
