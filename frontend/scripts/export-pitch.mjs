import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";
import { createHash } from "node:crypto";
import ts from "typescript";

const root = new URL("../../", import.meta.url);
const content = new URL("frontend/src/experience/", root);
const source = readFileSync(new URL("pitch.ts", content), "utf8");
const compiled = ts.transpileModule(
  source.replace("import.meta.env.VITE_SYMBIOSE_APP_URL", "undefined"),
  {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  },
).outputText;
const { pitchChapters, juryCoverage, clock, statusLabels } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

const evidence = ["caen", "carentan"].map((name) => {
  const path = `docs/evidence/territorial/${name}.json.gz`;
  const bytes = readFileSync(new URL(path, root));
  const archive = JSON.parse(gunzipSync(bytes));
  return {
    place: name === "caen" ? "Caen" : "Carentan",
    location: archive.location,
    created_at: archive.created_at,
    mode: archive.mode,
    origin: archive.origin,
    archive: path,
    archive_sha256: createHash("sha256").update(bytes).digest("hex"),
    layers: Object.values(archive.layers).map((layer) => ({
      code: layer.layer,
      status: layer.status,
      source_url: layer.source_url,
      retrieved_at: layer.retrieved_at,
      sha256: layer.sha256,
      features: layer.features.map(({ name, source_id }) => ({
        name,
        source_id,
      })),
    })),
  };
});

const words = pitchChapters
  .filter((c) => c.id !== "meadow")
  .map((c) => c.oral)
  .join(" ")
  .split(/\s+/).length;
let doc =
  `# Symbiose — pitch du Datathon Normandie 2026\n\n` +
  `Généré depuis [pitch.ts](../frontend/src/experience/pitch.ts) par \`node frontend/scripts/export-pitch.mjs\`.\n\n` +
  `Durée cible : **5 minutes**, dont **90 secondes** de démonstration manuelle. ` +
  `Le texte hors vidéo compte environ **${words} mots**, soit **${Math.round(words / 3.5)} mots/minute** sur 3 min 30. ` +
  `C’est une estimation éditoriale : une répétition avec les transitions et les pauses reste nécessaire.\n\n` +
  `## État des sources et limites\n\n` +
  `Le manifeste final ARQ (13 pages, dont les captures), le règlement fourni (5 pages), la trame de descriptif DOCX (vierge), l’image des cinq questions, les guides du dépôt, les recettes techniques et les archives territoriales ont été examinés. ` +
  `Le manifeste répond aux sept rubriques de la trame : solution et équipe, mots-clés, problème, cibles, bénéfices attendus, producteurs et liens des données, accès et captures. Les sources externes mentionnées sont celles utilisées par le code ; aucune actualisation réseau n’est réalisée par cette présentation. ` +
  `Le règlement § 5, p. 3 donne six critères : pertinence thématique, originalité, innovation, sobriété numérique, faisabilité et qualité orale. L’image fournie fixe les cinq questions. La correspondance ci-dessous les couvre sans prétendre certifier l’ensemble des obligations administratives du concours. ` +
  `Le § 3 du règlement mentionne emploi-formation et cite les données de biodiversité dans sa note de bas de page ; cette ambiguïté du document n’est pas réécrite. ` +
  `La vidéo produit de 90 secondes sera réalisée en aval par l’équipe. Le remplacement est une capture de validation humaine extraite du manifeste, page 7, et non une vidéo ou une preuve de performance. ` +
  `Les vidéos de navigation archivées et la vidéo d’écureuil ne remplacent pas une démonstration produit.\n\n` +
  `Les douze options de conception sont un inventaire fonctionnel documenté ; aucun gain écologique, gain de temps ou score de reconnaissance validé n’est annoncé. ` +
  `Les observations animales de la recette territoriale sont synthétiques. Les besoins de passage à l’échelle sont des propositions éditoriales à confirmer par l’équipe, sans partenaire acquis ni montant inventé.\n\n` +
  `## Déroulé chronométré\n\n`;
for (const chapter of pitchChapters) {
  doc +=
    `### ${clock(chapter.start)}–${clock(chapter.start + chapter.duration)} · ${chapter.subject} (${chapter.duration} s)\n\n` +
    `**Message principal :** ${chapter.message}\n\n` +
    `**Statut :** ${statusLabels[chapter.status]}.\n\n` +
    `**Texte oral proposé :** ${chapter.oral}\n\n` +
    `**Écran :** ${chapter.title.replaceAll("\n", " ")} — ${chapter.screen.join(" ; ")}.\n\n` +
    `**Interaction / animation :** ${chapter.interaction}\n\n` +
    `**Transition :** ${chapter.transition}\n\n` +
    `**Sources locales :** ${chapter.sources.join(", ")} (voir registre ci-dessous et carnet de sources dans l’expérience).\n\n`;
}
doc +=
  `## Correspondance avec les attendus du jury\n\n| Attendu de la demande | Scènes | Couverture |\n|---|---|---|\n` +
  juryCoverage.map((row) => `| ${row.join(" | ")} |`).join("\n") +
  "\n\n" +
  `## Registre de sources\n\n` +
  `| Identifiant | Document |\n|---|---|\n` +
  `| annex | annexe_règlement_datathon_2026 (1).pdf, § 3 (thématique), § 4 (livrables), § 5 (six critères) ; transcription locale embarquée |\n` +
  `| description | Descriptif_projet_Datathon (1).docx : trame vierge à sept rubriques ; aucun résultat supplémentaire |\n` +
  `| jury-questions | image (4).png : problème, solution, impacts, équipe, besoins pour changer d’échelle |\n` +
  `| manifesto | Manifeste - Symbiose - Equipe ARQ.pdf, p. 1–3 (discours) et 3–13 (application) ; transcription locale embarquée et capture p. 7 |\n` +
  `| architecture | [README](../README.md), socle local et exploitation |\n` +
  `| parcels | [Parcelles et données utilisées](PARCEL_DOSSIERS.md) |\n` +
  `| territory | [Contexte territorial](TERRITORIAL_CONTEXT.md) |\n` +
  `| territory-validation | [Recette et archives IGN](TERRITORIAL_VALIDATION.md) |\n` +
  `| wetlands | [DREAL Normandie](DREAL_WETLANDS.md) |\n` +
  `| design | [Alternatives de conception](PROJECT_DESIGN.md) |\n` +
  `| design-validation | [Recette des alternatives](PROJECT_DESIGN_VALIDATION.md) |\n` +
  `| vision | [Pipeline vision](../workers/vision/INFERENCE.md) |\n` +
  `| review | [Validation humaine](../HUMAN_REVIEW.md) |\n` +
  `| documents | [Worker scientifique](../workers/documents/README.md) |\n` +
  `| rag | [Recherche et génération documentaires](RAG.md) |\n\n` +
  `## Deux modes de lecture\n\n` +
  `- Exploration : scroll libre, huit chapitres, carnet de sources et détails techniques.\n` +
  `- Présentation : flèches gauche/droite ou Page précédente/suivante, Début/Fin, Espace pour lire/pause ; arrêt automatique au prochain chapitre. Les contrôles, dialogues et le lecteur conservent leurs touches natives.\n` +
  `- Le raccourci Démonstration rejoint 2:30. La vidéo se lance seulement par geste utilisateur, se met en pause en quittant la scène, à l’ouverture du carnet et lorsque l’onglet est masqué.\n` +
  `- Le compteur indique la position dans le script de cinq minutes, pas le temps réel de parole ni le temps joué par le média. La démonstration est manuelle et ne déclenche aucune reprise automatique du récit.\n` +
  `- Plein écran sur action explicite, avec message si l’API est indisponible ; les mouvements réduits gardent la navigation et désactivent la lecture animée.\n\n` +
  `## Lancer et configurer\n\n` +
  "```powershell\ncd frontend\nnpm.cmd run dev\n# Build typé et tests sans GPU IA\nnpm.cmd run build\nnpm.cmd test\nnpm.cmd run test:e2e -- pitch.spec.ts narrative.spec.ts\n# Régénérer ce document et la matrice d’archives après modification des sources\nnode scripts/export-pitch.mjs\n```\n\n" +
  `Avec le socle habituel : \`docker compose up -d --build --no-deps frontend\`. Ouvrir \`http://localhost:8080/\` hors session ; une session active conserve l’accueil métier existant. ` +
  `Tous les médias, textes, géométries et archives de cette expérience sont servis localement. Les liens vers les producteurs restent facultatifs et nécessitent Internet ; le backend et les services publics restent nécessaires pour analyser de nouvelles données dans l’application.\n\n` +
  `Déposer la vraie vidéo dans \`frontend/public/experience-media/demo.mp4\` ou \`demo.webm\` puis reconstruire. ` +
  `On peut aussi choisir un fichier local depuis la scène, sans téléversement. ` +
  `Configuration au build Vite : \`VITE_SYMBIOSE_APP_URL\` (défaut \`/connexion\`), \`VITE_SYMBIOSE_DEMO_URL\` (chemin local absolu optionnel), \`VITE_SYMBIOSE_DEMO_CAPTIONS_URL\` (WebVTT français local optionnel). ` +
  `Avec Docker, passer ces variables depuis \`frontend/.env.local\` (fichier ignoré copié au build) ; les variables de conteneur à l’exécution ne reconfigurent pas les fichiers statiques. ` +
  `Une configuration média distante est refusée. Un fichier absent ou illisible affiche un état explicite. Fournir les sous-titres et une vidéo de 90 s pour la recette finale ; le lecteur avertit si la durée s’en écarte de plus de 5 s.\n`;

const outputs = [
  [
    new URL("content/source-documents.json", content),
    JSON.stringify(
      Object.fromEntries(
        [
          "README.md",
          "docs/PARCEL_DOSSIERS.md",
          "docs/TERRITORIAL_CONTEXT.md",
          "docs/TERRITORIAL_VALIDATION.md",
          "docs/DREAL_WETLANDS.md",
          "docs/PROJECT_DESIGN.md",
          "docs/PROJECT_DESIGN_VALIDATION.md",
          "workers/vision/INFERENCE.md",
          "HUMAN_REVIEW.md",
          "workers/documents/README.md",
          "docs/RAG.md",
        ].map((path) => [
          path,
          readFileSync(new URL(path, root), "utf8").replaceAll("\r\n", "\n"),
        ]),
      ),
      null,
      2,
    ) + "\n",
  ],
  [
    new URL("content/territorial-evidence.json", content),
    JSON.stringify(evidence, null, 2) + "\n",
  ],
  [new URL("docs/PITCH_DATATHON_2026.md", root), doc],
];
for (const [url, value] of outputs) {
  if (process.argv.includes("--check")) {
    if (readFileSync(url, "utf8") !== value)
      throw new Error(`À régénérer : ${fileURLToPath(url)}`);
  } else writeFileSync(url, value, "utf8");
}
console.log(
  `${words} mots hors vidéo ; 300 secondes prévues ; sources et exports ${process.argv.includes("--check") ? "à jour" : "générés"}.`,
);
