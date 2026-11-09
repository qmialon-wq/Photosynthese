import { ref } from "vue";
export const lastObservationRoute = ref("/");
export const adminSections = [
  { path: "/admin/utilisateurs", label: "Utilisateurs", icon: "user" },
  { path: "/admin", label: "Vue d’ensemble", icon: "grid" },
  { path: "/admin/videos", label: "Gestion des vidéos", icon: "video" },
  { path: "/admin/analyses", label: "Réglages d’analyse", icon: "sliders" },
  { path: "/admin/datasets", label: "Datasets", icon: "layers" },
  { path: "/admin/training", label: "Entraînements", icon: "sparkles" },
  { path: "/admin/models", label: "Modèles", icon: "box" },
  { path: "/admin/evaluation", label: "Évaluation", icon: "chart" },
  {
    path: "/admin/documents",
    label: "Documents scientifiques",
    icon: "document",
  },
] as const;
