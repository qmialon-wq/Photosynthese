export const clientGuideCards = [
  {
    title: "Bienvenue dans votre espace Symbiose",
    eyebrow: "Votre première visite",
    intro:
      "De la vidéo de terrain au dossier biodiversité, vous gardez la main sur chaque observation. Ce guide présente le parcours client en 2–3 minutes.",
    bullets: [
      "Importez vos vidéos, puis choisissez le niveau d’analyse souhaité.",
      "Vérifiez les espèces proposées et regroupez vos vidéos par parcelle.",
      "Le bouton ? Aide permet de retrouver ce guide à tout moment.",
    ],
    image: "home",
    alt: "Accueil connecté avec ses raccourcis et l’accès au guide",
    marks: [
      { x: 40, y: 48, label: "Les étapes de votre parcours" },
      { x: 94, y: 6, label: "Aide, toujours disponible" },
    ],
  },
  {
    title: "Importez vos vidéos de terrain",
    eyebrow: "01 · Vidéothèque",
    intro:
      "Ouvrez Vidéothèque, puis Importer des vidéos. Vous pouvez choisir plusieurs fichiers depuis votre ordinateur et les envoyer ensemble.",
    bullets: [
      "Patientez pendant le transfert, puis la préparation en arrière-plan : le suivi affiche l’état de chaque fichier.",
      "Vos vidéos restent disponibles dans la vidéothèque pour une analyse ou un dossier.",
      "Un nom de fichier peut suggérer une espèce ; il ne confirme jamais les animaux présents.",
    ],
    image: "videos",
    alt: "Vidéothèque avec le bouton Importer des vidéos et les captures disponibles",
    marks: [
      { x: 86, y: 18, label: "Importer des vidéos" },
      { x: 36, y: 80, label: "Vos captures et leur aperçu" },
    ],
  },
  {
    title: "Lancez une première analyse",
    eyebrow: "02 · Analyse vidéo",
    intro:
      "Dans Analyses, choisissez votre vidéo. Sélectionnez la détection seule ou l’identification des espèces lorsqu’un classificateur actif est disponible, puis le niveau de détail.",
    bullets: [
      "Lancer l’analyse soumet une tâche : vous pouvez continuer à naviguer pendant son traitement.",
      "Retrouvez ensuite la vidéo annotée, les détections et le rapport dans Analyses.",
      "Le mode rapide examine moins d’images et peut manquer un passage bref. Une analyse peut aussi ne détecter aucun animal.",
    ],
    image: "analysis",
    alt: "Formulaire d’analyse avec les réglages et le bouton de lancement",
    marks: [
      { x: 60, y: 44, label: "Réglez l’analyse" },
      { x: 54, y: 80, label: "Lancez le traitement" },
    ],
  },
  {
    title: "Ajoutez une validation humaine",
    eyebrow: "03 · Confirmer les espèces",
    intro:
      "Pour vérifier les identifications, utilisez Confirmer les espèces sur l’écran d’analyse. Cette action prépare des images et recadrages à examiner dans Validation humaine.",
    bullets: [
      "La préparation des recadrages est une tâche distincte de l’analyse vidéo : attendez sa fin.",
      "Vous pouvez faire une analyse rapide, puis confirmer les espèces, ou préparer directement les recadrages d’une vidéo.",
      "Les résultats automatiques restent des propositions jusqu’à votre vérification.",
    ],
    image: "analysis",
    alt: "Analyse vidéo et accès à la préparation des recadrages",
    marks: [{ x: 54, y: 88, label: "Préparer les images à vérifier" }],
  },
  {
    title: "Corrigez vos observations",
    eyebrow: "04 · Validation humaine",
    intro:
      "Ouvrez Validation humaine pour retrouver vos images à revoir. Les filtres permettent de cibler un état, une espèce ou une qualité d’image.",
    bullets: [
      "Ouvrez une image, choisissez l’espèce et ajustez le cadre si nécessaire avant de confirmer.",
      "Pour plusieurs images de la même espèce, sélectionnez-les puis utilisez Valider la sélection.",
      "Rejetez les exemples inutilisables. Les images de test gelées sont protégées ; vos corrections conservent un historique.",
    ],
    image: "review",
    alt: "File de validation humaine avec la sélection d’images et les actions de correction",
    marks: [
      { x: 21, y: 31, label: "Filtrez les observations" },
      { x: 44, y: 43, label: "Validez une sélection" },
      { x: 14, y: 72, label: "Ouvrez une image pour la corriger" },
    ],
  },
  {
    title: "Créez un dossier pour votre parcelle",
    eyebrow: "05 · Mes dossiers",
    intro:
      "Dans Vidéothèque, importez ou sélectionnez les vidéos d’une même parcelle, puis cliquez sur Préparer un dossier. Vous renseignez votre projet une seule fois pour toutes ces vidéos.",
    bullets: [
      "Précisez la parcelle, sa localisation et les interventions envisagées. Vérifiez les informations préremplies.",
      "Retrouvez le dossier dans Mes dossiers pour compléter le formulaire, suivre les traitements et consulter les résultats.",
      "Les recommandations dépendent des observations confirmées et des sources disponibles. Elles restent à examiner selon votre terrain.",
    ],
    image: "projects",
    alt: "Vidéothèque avec des vidéos sélectionnées et le bouton Préparer un dossier",
    marks: [
      { x: 6, y: 74, label: "Sélectionnez les vidéos d’une parcelle" },
      { x: 54, y: 49, label: "Préparez un dossier commun" },
    ],
  },
  {
    title: "Explorez les documents scientifiques",
    eyebrow: "06 · Comprendre et approfondir",
    intro:
      "Documents scientifiques donne accès à la bibliothèque commune. Parcourez les publications par espèce, puis ouvrez un document pour lire les passages disponibles et consulter sa source.",
    bullets: [
      "Les textes en français ou traduits facilitent la lecture ; vous pouvez retrouver l’original.",
      "Votre compte client permet la consultation. La collecte, l’import et le retrait des publications sont réservés à l’administration.",
      "Les références de vos dossiers permettent de revenir aux éléments qui soutiennent une recommandation.",
    ],
    image: "documents",
    alt: "Bibliothèque scientifique avec le filtre par espèce et l’ouverture d’un document",
    marks: [
      { x: 18, y: 45, label: "Choisissez une espèce" },
      { x: 89, y: 54, label: "Lisez le document et sa source" },
    ],
  },
  {
    title: "Vous êtes prêt à commencer",
    eyebrow: "À votre rythme",
    intro:
      "Commencez avec quelques vidéos. Le parcours habituel est simple : importer, analyser, vérifier les espèces, puis retrouver les résultats dans votre dossier.",
    bullets: [
      "Accueil résume vos dernières analyses et propose les raccourcis utiles.",
      "Mon profil permet de modifier vos informations, d’exporter vos données et de gérer votre compte.",
      "Besoin d’un rappel ? Le bouton ? Aide relance ces cartes, sans modifier vos vidéos ni lancer de traitement.",
    ],
    image: "home",
    alt: "Accueil de l’espace client et raccourcis pour démarrer",
    marks: [{ x: 42, y: 49, label: "Commencez par vos vidéos" }],
  },
] as const;
