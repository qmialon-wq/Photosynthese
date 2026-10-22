import { createRouter, createWebHistory } from "vue-router";

export const navigation = [
  { path: "/", label: "Vue d’ensemble", icon: "pi-th-large" },
  { path: "/videos", label: "Vidéothèque", icon: "pi-video" },
  { path: "/analyses", label: "Analyses", icon: "pi-sparkles" },
  { path: "/review", label: "Validation humaine", icon: "pi-check-square" },
  { path: "/datasets", label: "Datasets", icon: "pi-database" },
  { path: "/training", label: "Entraînements", icon: "pi-bolt" },
  { path: "/models", label: "Modèles", icon: "pi-box" },
  { path: "/evaluation", label: "Évaluation", icon: "pi-chart-bar" },
];
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("./pages/DashboardPage.vue") },
    { path: "/videos", component: () => import("./pages/VideosPage.vue") },
    { path: "/analyses", component: () => import("./pages/AnalysisPage.vue") },
    { path: "/review", component: () => import("./pages/ReviewPage.vue") },
    { path: "/datasets", component: () => import("./pages/DatasetsPage.vue") },
    { path: "/training", component: () => import("./pages/TrainingPage.vue") },
    { path: "/models", component: () => import("./pages/ModelsPage.vue") },
    {
      path: "/evaluation",
      component: () => import("./pages/EvaluationPage.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
