// Données de présentation uniquement : aucun appel réseau ni calcul métier.
export const journey = [
  {
    step: "01 · IMPORTER",
    icon: "video",
    title: "Vos vidéos de terrain",
    description:
      "Importez plusieurs vidéos ou sélectionnez celles de votre parcelle.",
    action: "Ouvrir la vidéothèque",
    path: "/videos",
  },
  {
    step: "02 · DÉCRIRE VOTRE PROJET",
    icon: "sparkles",
    title: "Votre parcelle, votre projet",
    description:
      "Indiquez la surface, le type de terrain et l’activité souhaitée.",
    action: "Voir les analyses",
    path: "/analyses",
  },
  {
    step: "03 · RETROUVER VOS RÉSULTATS",
    icon: "check-square",
    title: "Un dossier pour aménager",
    description:
      "Confirmez les espèces, consultez les pistes sourcées et téléchargez votre dossier.",
    action: "Vidéo annotée et dossier",
    path: "/parcelles",
  },
];
export const indicators = [
  { icon: "paw", label: "Diversité des espèces", value: 82 },
  { icon: "camera", label: "Qualité des habitats", value: 76 },
  { icon: "connection", label: "Connectivité écologique", value: 71 },
  { icon: "layers", label: "Niveau de connaissance", value: 68 },
];
