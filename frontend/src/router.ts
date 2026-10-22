import { createRouter, createWebHistory } from "vue-router";

export const navigation = [
  { path: "/", label: "Accueil", icon: "pi-th-large" },
  { path: "/videos", label: "Vidéothèque", icon: "pi-video" },
  { path: "/analyses", label: "Analyses", icon: "pi-sparkles" },
  { path: "/review", label: "Validation humaine", icon: "pi-check-square" },
];
export const adminNavigation = [
  { path: "/admin", label: "Vue d’ensemble", icon: "pi-th-large" },
  { path: "/admin/videos", label: "Gestion des vidéos", icon: "pi-video" },
  {
    path: "/admin/analyses",
    label: "Réglages d’analyse",
    icon: "pi-sliders-h",
  },
  { path: "/admin/datasets", label: "Datasets", icon: "pi-database" },
  { path: "/admin/training", label: "Entraînements", icon: "pi-bolt" },
  { path: "/admin/models", label: "Modèles", icon: "pi-box" },
  { path: "/admin/evaluation", label: "Évaluation", icon: "pi-chart-bar" },
];
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("./pages/HomePage.vue") },
    { path: "/admin", component: () => import("./pages/DashboardPage.vue") },
    {
      path: "/admin/videos",
      component: () => import("./pages/VideosPage.vue"),
    },
    {
      path: "/admin/analyses",
      component: () => import("./pages/AnalysisPage.vue"),
    },
    { path: "/videos", component: () => import("./pages/VideosPage.vue") },
    { path: "/analyses", component: () => import("./pages/AnalysisPage.vue") },
    { path: "/review", component: () => import("./pages/ReviewPage.vue") },
    ...["datasets", "training", "models", "evaluation"].map((page) => ({
      path: `/${page}`,
      redirect: (to: import("vue-router").RouteLocation) => ({
        path: `/admin/${page}`,
        query: to.query,
        hash: to.hash,
      }),
    })),
    {
      path: "/admin/datasets",
      component: () => import("./pages/DatasetsPage.vue"),
    },
    {
      path: "/admin/training",
      component: () => import("./pages/TrainingPage.vue"),
    },
    {
      path: "/admin/models",
      component: () => import("./pages/ModelsPage.vue"),
    },
    {
      path: "/admin/evaluation",
      component: () => import("./pages/EvaluationPage.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
