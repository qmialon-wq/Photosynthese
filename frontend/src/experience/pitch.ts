import type { ChapterId } from "./config";

export type EvidenceStatus = "operational" | "measured" | "expected" | "future";
export const statusLabels: Record<EvidenceStatus, string> = {
  operational: "Fonction documentée",
  measured: "Résultat technique vérifié",
  expected: "Bénéfice attendu · non mesuré",
  future: "Perspective · non opérationnelle",
};
export interface PitchChapter {
  id: ChapterId;
  subject: string;
  title: string;
  message: string;
  status: EvidenceStatus;
  start: number;
  duration: number;
  oral: string;
  screen: string[];
  interaction: string;
  transition: string;
  sources: string[];
}

export const pitchDuration = 300;
// Preserve the existing spatial study and all seven reversible camera transitions.
// Presentation seconds are an editorial clock, independent of the 210-unit camera path.
export const visualBoundaries = [
  0, 17.5, 47.5, 77.5, 105, 132.5, 165, 195, 210,
];
export const pitchChapters: readonly PitchChapter[] = [
  {
    id: "forest",
    subject: "Le problème",
    title: "Voir le vivant.\nÉclairer nos choix.",
    message:
      "Des observations dispersées. Des projets à éclairer à l’échelle locale.",
    status: "expected",
    start: 0,
    duration: 35,
    oral: "Une caméra piège filme un animal. Mais comment passer de cette observation à une décision d’aménagement ? Les vidéos, les inventaires et les études existent ; ils restent dispersés et longs à analyser. Pour une collectivité, un agriculteur ou un aménageur, connaître les enjeux locaux reste difficile. Symbiose veut relier ces informations pour éclairer les choix, avant les travaux.",
    screen: ["Observer", "Comprendre", "Préparer la décision"],
    interaction:
      "Une caméra piège et une silhouette animale illustrent une observation candidate, sans score inventé.",
    transition: "La caméra quitte le sous-bois et prend de la hauteur.",
    sources: ["manifesto", "description", "jury-questions"],
  },
  {
    id: "sky",
    subject: "La vision",
    title: "Un territoire.\nDes liens à comprendre.",
    message:
      "Symbiose relie observations, connaissances et projets d’aménagement.",
    status: "operational",
    start: 35,
    duration: 25,
    oral: "Notre solution, Symbiose, associe reconnaissance animale, validation humaine et données du territoire. Elle s’adresse aux collectivités, aux propriétaires, aux aménageurs et aux naturalistes. Son originalité : partir d’un projet concret et rendre visibles les preuves, les incertitudes et les adaptations à examiner. L’humain garde la décision.",
    screen: [
      "Collectivités",
      "Agriculteurs et propriétaires",
      "Aménageurs et naturalistes",
    ],
    interaction:
      "Le survol révèle les liens entre les milieux normands ; le trajet reste illustratif.",
    transition: "Le regard suit la vallée et rejoint le réseau des rivières.",
    sources: ["manifesto", "parcels", "design", "annex"],
  },
  {
    id: "rivers",
    subject: "Les données",
    title: "Faire converger\nles connaissances.",
    message:
      "Observations validées, cadastre, occupation agricole et référentiels environnementaux.",
    status: "operational",
    start: 60,
    duration: 35,
    oral: "Le prototype croise les vidéos validées avec le cadastre, les prairies déclarées au RPG 2024, les zonages IGN et les zones humides de la DREAL Normandie. OpenAlex, Crossref et Europe PMC alimentent la recherche documentaire. Chaque source garde sa provenance. Les consultations archivées de Caen et Carentan montrent un fonctionnement technique ; elles ne mesurent aucun effet écologique. Un point consulté ne décrit pas toute une parcelle.",
    screen: [
      "Vidéos et validation humaine",
      "Cadastre · RPG 2024 · commune",
      "ZNIEFF · Natura 2000 · zones humides",
      "Publications scientifiques",
    ],
    interaction:
      "Quatre affluents documentaires convergent ; une matrice interactive montre les réponses IGN réellement archivées.",
    transition:
      "Le courant entraîne le regard sous la surface, vers une perspective d’évolution.",
    sources: [
      "manifesto",
      "parcels",
      "territory",
      "territory-validation",
      "wetlands",
      "documents",
    ],
  },
  {
    id: "underwater",
    subject: "Les perspectives",
    title: "Demain,\nécouter aussi le vivant.",
    message:
      "Hydrophones, caméras immergées et autres capteurs : des pistes à développer et à valider.",
    status: "future",
    start: 95,
    duration: 20,
    oral: "Aujourd’hui, nous travaillons sur les vidéos terrestres. Demain, des hydrophones ou des caméras immergées pourraient élargir l’observation. Ce sont des perspectives : ces capteurs ne sont pas opérationnels dans le prototype. Chaque nouveau milieu demandera des données et une validation adaptées.",
    screen: [
      "Hydrophones",
      "Caméras immergées",
      "Nouveaux protocoles à valider",
    ],
    interaction:
      "Des ondes illustratives évoquent l’écoute ; aucun signal acoustique réel n’est revendiqué.",
    transition:
      "La caméra remonte vers les roseaux et la chaîne d’analyse actuelle.",
    sources: ["manifesto", "vision"],
  },
  {
    id: "wetland",
    subject: "Le moteur technique",
    title: "L’IA propose.\nL’humain vérifie.",
    message:
      "De la vidéo au dossier : une chaîne traçable, avec des étapes distinctes.",
    status: "operational",
    start: 115,
    duration: 35,
    oral: "Nous extrayons des images de la vidéo. MegaDetector localise les animaux ; un modèle PyTorch propose une espèce, puis le suivi relie les observations dans le temps. La personne vérifie l’espèce et le recadrage. Les données ouvertes et les publications enrichissent ensuite le dossier. Les traitements sont locaux et asynchrones, avec une seule tâche GPU lourde à la fois. Aucun entraînement ne démarre automatiquement.",
    screen: [
      "Vidéo",
      "Extraction",
      "Reconnaissance et suivi",
      "Validation humaine",
      "Open Data et publications",
      "Pistes d’aménagement",
    ],
    interaction:
      "Un fil lumineux traverse six étapes dans le paysage ; chaque étape explique son rôle au clic.",
    transition:
      "Les annotations se rapprochent et deviennent le cadre de la démonstration produit.",
    sources: ["vision", "review", "rag", "architecture"],
  },
  {
    id: "meadow",
    subject: "La démonstration",
    title: "Du terrain\nà un dossier partagé.",
    message:
      "90 secondes dans l’application. Lecture et pause sous votre contrôle.",
    status: "operational",
    start: 150,
    duration: 90,
    oral: "[Démonstration vidéo locale : 90 secondes. Lancer manuellement. Montrer l’import, la validation d’une observation, le projet localisé, ses sources et une alternative conditionnelle. Si la vidéo est absente, annoncer le remplacement par une capture issue du manifeste ; ne pas prétendre avoir démontré le parcours complet.]",
    screen: [
      "Importer les vidéos",
      "Valider une observation",
      "Examiner un projet et ses sources",
    ],
    interaction:
      "Lecteur HTML natif, sans lecture automatique. Capture du manifeste en remplacement et sélection possible d’un fichier vidéo local.",
    transition:
      "Le cadre de l’interface s’ouvre à nouveau sur le bocage puis le littoral.",
    sources: ["manifesto", "parcels", "review", "design-validation"],
  },
  {
    id: "coast",
    subject: "Les impacts",
    title: "Mieux anticiper.\nMieux adapter.",
    message:
      "Des bénéfices attendus pour les acteurs normands ; leur ampleur reste à évaluer sur le terrain.",
    status: "expected",
    start: 240,
    duration: 25,
    oral: "Le prototype documente douze alternatives pour cinq types d’intervention, dont les clôtures et l’éclairage. Les bénéfices attendus sont un examen facilité des observations et des projets mieux informés. Ces options restent conditionnelles : leur efficacité locale n’est pas mesurée. Il faut vérifier les habitats, les usages et l’applicabilité des sources avec les acteurs du terrain.",
    screen: [
      "Collectivité : examiner un éclairage",
      "Propriétaire : étudier une clôture",
      "Aménageur : revoir une implantation",
    ],
    interaction:
      "Trois usages se déploient devant une évocation discrète d’Étretat ; le nombre d’alternatives est relié à sa source.",
    transition:
      "La lumière baisse ; les liens du territoire rejoignent la forêt nocturne.",
    sources: ["manifesto", "design", "design-validation"],
  },
  {
    id: "night-forest",
    subject: "L’équipe et la suite",
    title:
      "Pour mieux protéger le vivant,\ncommençons par mieux le comprendre.",
    message:
      "ARQ · Arden, Romain et Quentin. Passer du prototype à une évaluation de terrain.",
    status: "future",
    start: 265,
    duration: 35,
    oral: "Nous sommes ARQ : Arden, Romain et Quentin. Pour changer d’échelle, nous proposons de rechercher des terrains pilotes en Normandie, un accompagnement naturaliste et des moyens de consolidation technique. Les prochaines étapes : valider les observations, mesurer l’utilité pour les utilisateurs et évaluer les ressources consommées. Aucun partenariat n’est annoncé. Pour mieux protéger le vivant, commençons par mieux le comprendre.",
    screen: [
      "Terrains pilotes à rechercher",
      "Expertise naturaliste à mobiliser",
      "Robustesse et sobriété à évaluer",
    ],
    interaction:
      "Le logo apparaît avec un lien configurable vers la connexion ou l’inscription.",
    transition:
      "Arrêt final. L’utilisateur choisit d’entrer dans l’application.",
    sources: ["manifesto", "architecture", "design-validation"],
  },
];

export const juryCoverage = [
  [
    "Problème",
    "Forêt",
    "Données dispersées et difficulté à préparer une décision locale.",
  ],
  [
    "Solution",
    "Ciel · Zone humide · Démonstration",
    "Chaîne vidéo, contrôle humain et dossier contextualisé.",
  ],
  [
    "Impacts",
    "Littoral",
    "Bénéfices attendus séparés des mesures techniques ; pas de gain écologique chiffré.",
  ],
  [
    "Équipe",
    "Forêt nocturne",
    "ARQ : Arden, Romain et Quentin ; rôles individuels non documentés.",
  ],
  [
    "Besoins pour changer d’échelle",
    "Forêt nocturne",
    "Proposition : pilotes, expertise et consolidation ; aucun partenaire ni financement acquis.",
  ],
  [
    "Originalité",
    "Ciel · Démonstration",
    "Partir des interventions du projet et rendre les preuves consultables.",
  ],
  [
    "Innovation",
    "Zone humide",
    "Vision, validation humaine et recherche documentaire reliées aux interventions.",
  ],
  [
    "Données ouvertes",
    "Rivières",
    "Producteurs, usages, millésime RPG et limites des consultations ponctuelles.",
  ],
  [
    "Faisabilité",
    "Zone humide · Démonstration",
    "Socle local existant, recettes techniques archivées et lecteur local.",
  ],
  [
    "Numérique responsable",
    "Zone humide · Forêt nocturne",
    "Traitements locaux, GPU sérialisé ; consommation et utilité à mesurer.",
  ],
  [
    "Pertinence territoriale",
    "Rivières · Littoral",
    "Sources DREAL Normandie et archives de points normands ; usages proposés aux acteurs locaux.",
  ],
  [
    "Qualité de la présentation orale",
    "Ensemble du parcours",
    "Script de 5 minutes, 90 secondes réservées à la vidéo, mots simples et arrêts manuels ; répétition à effectuer.",
  ],
] as const;

export const pitchWordCount = pitchChapters
  .filter((chapter) => chapter.id !== "meadow")
  .map((chapter) => chapter.oral)
  .join(" ")
  .split(/\s+/).length;

export const clock = (seconds: number) =>
  `${Math.floor((seconds + 1e-6) / 60)}:${String(Math.floor((seconds + 1e-6) % 60)).padStart(2, "0")}`;

export function pitchIndex(progress: number): number {
  const units =
    Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0)) * 210;
  const index = visualBoundaries.findIndex(
    (end, i) => i > 0 && units < end - 1e-8,
  );
  return index === -1 ? 7 : index - 1;
}
export function pitchSeconds(progress: number): number {
  const index = pitchIndex(progress),
    chapter = pitchChapters[index];
  const units =
    Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0)) * 210;
  return (
    chapter.start +
    (chapter.duration * (units - visualBoundaries[index])) /
      (visualBoundaries[index + 1] - visualBoundaries[index])
  );
}
export function progressAtSeconds(seconds: number): number {
  const value = Math.min(
    pitchDuration,
    Math.max(0, Number.isFinite(seconds) ? seconds : 0),
  );
  const index = pitchChapters.findIndex(
    (chapter) => value < chapter.start + chapter.duration,
  );
  if (index === -1) return 1;
  const chapter = pitchChapters[index];
  return (
    (visualBoundaries[index] +
      ((value - chapter.start) / chapter.duration) *
        (visualBoundaries[index + 1] - visualBoundaries[index])) /
    210
  );
}
export const chapterProgress = (index: number) =>
  progressAtSeconds(pitchChapters[Math.min(7, Math.max(0, index))].start);

export function applicationUrl(value?: string): string {
  const candidate = value?.trim();
  if (!candidate) return "/connexion";
  if (/^\/(?![\/\\])/.test(candidate) && !candidate.includes("\\"))
    return candidate;
  try {
    const url = new URL(candidate);
    if (["http:", "https:"].includes(url.protocol)) return url.href;
  } catch {
    /* Invalid configuration falls back to the existing login route. */
  }
  return "/connexion";
}

export const appUrl = applicationUrl(import.meta.env.VITE_SYMBIOSE_APP_URL);
export function localMediaUrl(value?: string): string {
  const candidate = value?.trim() ?? "";
  return /^\/(?![\/\\])/.test(candidate) && !/[\\?#\s]/.test(candidate)
    ? candidate
    : "";
}
