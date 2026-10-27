import { createRouter, createWebHistory } from "vue-router";
import { api, ApiError, message } from "./api";
import { auth, acceptSession, clearSession, type Session } from "./auth-state";

export const navigation = [
  { path: "/", label: "Accueil", icon: "pi-th-large" },
  { path: "/videos", label: "Vidéothèque", icon: "pi-video" },
  { path: "/parcelles", label: "Mes dossiers", icon: "pi-folder" },
  { path: "/analyses", label: "Analyses", icon: "pi-sparkles" },
  { path: "/review", label: "Validation humaine", icon: "pi-check-square" },
  { path: "/documents", label: "Documents scientifiques", icon: "pi-book" },
];
export const adminNavigation = [
  { path: "/admin/utilisateurs", label: "Utilisateurs", icon: "pi-users" },
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
  {
    path: "/admin/documents",
    label: "Documents scientifiques",
    icon: "pi-book",
  },
];
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...["connexion", "inscription", "initialisation", "reinitialiser"].map(
      (page) => ({
        path: `/${page}`,
        component: () => import("./pages/AuthPage.vue"),
        meta: { public: true },
      }),
    ),
    { path: "/profil", component: () => import("./pages/ProfilePage.vue") },
    {
      path: "/admin/utilisateurs",
      component: () => import("./pages/UsersPage.vue"),
    },
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
    {
      path: "/parcelles",
      component: () => import("./pages/ParcelCorpusPage.vue"),
    },
    {
      path: "/parcelles/:id",
      component: () => import("./pages/ParcelCorpusPage.vue"),
    },
    { path: "/analyses", component: () => import("./pages/AnalysisPage.vue") },
    { path: "/review", component: () => import("./pages/ReviewPage.vue") },
    {
      path: "/documents",
      component: () => import("./pages/DocumentsPage.vue"),
    },
    {
      path: "/admin/documents",
      component: () => import("./pages/DocumentsPage.vue"),
    },
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

router.beforeEach(async (to) => {
  if (!auth.loaded) {
    try {
      acceptSession(await api<Session>("/auth/me"));
    } catch (error) {
      clearSession();
      if (!(error instanceof ApiError) || error.status !== 401)
        auth.error = message(error);
    }
  }
  if (to.meta.public) return;
  if (!auth.user) return { path: "/connexion" };
  if (to.path.startsWith("/admin") && auth.user.role !== "admin") return "/";
});
