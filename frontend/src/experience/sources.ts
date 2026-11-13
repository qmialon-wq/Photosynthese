import manifesto from "./content/manifesto.txt?raw";
import annex from "./content/datathon-annex.txt?raw";
import description from "./content/project-description.txt?raw";
// Repository excerpts are bundled explicitly so Docker's frontend-only build stays self-contained.
import texts from "./content/source-documents.json";
const architecture = texts["README.md"],
  parcels = texts["docs/PARCEL_DOSSIERS.md"],
  territory = texts["docs/TERRITORIAL_CONTEXT.md"],
  territoryValidation = texts["docs/TERRITORIAL_VALIDATION.md"],
  wetlands = texts["docs/DREAL_WETLANDS.md"],
  design = texts["docs/PROJECT_DESIGN.md"],
  designValidation = texts["docs/PROJECT_DESIGN_VALIDATION.md"],
  vision = texts["workers/vision/INFERENCE.md"],
  review = texts["HUMAN_REVIEW.md"],
  documents = texts["workers/documents/README.md"],
  rag = texts["docs/RAG.md"];

export const sources = [
  {
    id: "annex",
    title: "Règlement officiel · annexe Datathon Normandie 2026",
    path: "annexe_règlement_datathon_2026 (1).pdf",
    scope:
      "5 pages. § 5, p. 3 : pertinence, originalité, innovation, sobriété numérique, faisabilité et qualité orale. § 3, p. 2 : le texte mentionne emploi-formation et cite la biodiversité dans sa note de bas de page. Cette ambiguïté éditoriale est conservée, sans réécrire le règlement.",
    text: annex,
  },
  {
    id: "description",
    title: "Trame du descriptif projet",
    path: "Descriptif_projet_Datathon (1).docx",
    scope:
      "Trame vierge à sept rubriques ; elle précise le format attendu, sans fournir de faits supplémentaires sur Symbiose. Le manifeste contient les réponses rédigées.",
    text: description,
  },
  {
    id: "jury-questions",
    title: "Les cinq questions de la présentation",
    path: "image (4).png",
    scope:
      "Image fournie par l’équipe, lue et transcrite ; correspondance avec les scènes dans l’onglet jury.",
    text: "Une présentation en 5 questions\nQuel est le problème ?\nQuelle est la solution ?\nQuels impacts ?\nQui compose l’équipe ?\nQuels sont les besoins pour changer d’échelle ?",
  },
  {
    id: "manifesto",
    title: "Manifeste final · équipe ARQ",
    path: "Manifeste - Symbiose - Equipe ARQ.pdf",
    scope:
      "p. 1–3 : projet, équipe, bénéfices attendus et données ; p. 3–13 : captures et description du prototype. Transcription du document fourni.",
    text: manifesto,
  },
  {
    id: "architecture",
    title: "Descriptif et architecture locale",
    path: "README.md",
    scope:
      "FastAPI, Vue, workers séparés, files asynchrones, modèles locaux et garde-fous GPU.",
    text: architecture,
  },
  {
    id: "parcels",
    title: "Parcelles et données réellement mobilisées",
    path: "docs/PARCEL_DOSSIERS.md",
    scope:
      "Commune, cadastre et RPG 2024 : suggestions à vérifier. Les déclarations utilisateur gardent leur provenance.",
    text: parcels,
  },
  {
    id: "territory",
    title: "Contexte territorial",
    path: "docs/TERRITORIAL_CONTEXT.md",
    scope:
      "Quatre couches IGN et analyse déterministe au point. Pas d’extrapolation à toute une emprise.",
    text: territory,
  },
  {
    id: "territory-validation",
    title: "Recette et archives IGN · 10 novembre 2026",
    path: "docs/TERRITORIAL_VALIDATION.md",
    scope:
      "Consultations réelles de deux points. Les observations animales des tests sont synthétiques. Aucun effet écologique mesuré.",
    text: territoryValidation,
  },
  {
    id: "wetlands",
    title: "DREAL Normandie · zones humides",
    path: "docs/DREAL_WETLANDS.md",
    scope:
      "Inventaire consulté ponctuellement ; couverture et qualité variables. La prédisposition n’est pas intégrée.",
    text: wetlands,
  },
  {
    id: "design",
    title: "Douze alternatives de conception",
    path: "docs/PROJECT_DESIGN.md",
    scope:
      "Cinq interventions ; propositions conditionnelles avec preuves et limites. Compensation non évaluée.",
    text: design,
  },
  {
    id: "design-validation",
    title: "Recette des alternatives",
    path: "docs/PROJECT_DESIGN_VALIDATION.md",
    scope:
      "Résultats techniques documentés ; captures navigateur basées sur des données de test. Efficacité locale non mesurée.",
    text: designValidation,
  },
  {
    id: "vision",
    title: "Détection, classification et suivi",
    path: "workers/vision/INFERENCE.md",
    scope:
      "Étapes séparées. Modèles à préparer explicitement, aucune performance scientifique déduite des captures.",
    text: vision,
  },
  {
    id: "review",
    title: "Validation humaine",
    path: "HUMAN_REVIEW.md",
    scope:
      "Confirmer, corriger ou rejeter l’espèce et le recadrage ; conserver l’historique.",
    text: review,
  },
  {
    id: "documents",
    title: "Recherche de publications scientifiques",
    path: "workers/documents/README.md",
    scope:
      "OpenAlex, Crossref et Europe PMC ; téléchargement conditionné aux droits disponibles.",
    text: documents,
  },
  {
    id: "rag",
    title: "Recherche et génération documentaires locales",
    path: "docs/RAG.md",
    scope:
      "Préparation explicite du modèle local. Les sources candidates ne deviennent pas automatiquement des preuves applicables.",
    text: rag,
  },
] as const;

export const producers = [
  ["Etalab / DINUM · commune", "https://geo.api.gouv.fr/"],
  ["IGN · cadastre", "https://apicarto.ign.fr/api/doc/cadastre"],
  [
    "IGN · occupation agricole, RPG 2024",
    "https://apicarto.ign.fr/api/doc/rpg",
  ],
  [
    "IGN / MNHN · ZNIEFF et Natura 2000",
    "https://apicarto.ign.fr/api/doc/nature",
  ],
  [
    "DREAL Normandie · zones humides inventoriées",
    "https://www.data.gouv.fr/datasets/zones-humides-normandie",
  ],
  ["OpenAlex", "https://openalex.org/"],
  ["Crossref", "https://www.crossref.org/"],
  ["Europe PMC", "https://europepmc.org/"],
] as const;
