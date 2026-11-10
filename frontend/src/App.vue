<script setup lang="ts">
import {
  computed,
  nextTick,
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
} from "vue";
import { useRoute } from "vue-router";
import { navigation, adminNavigation, router } from "./router";
import { auth, clearSession } from "./auth-state";
import { post, message } from "./api";
import AppShell from "./components/symbiose/AppShell.vue";
import ModeSelector from "./components/symbiose/ModeSelector.vue";
import { useDataMode } from "./data/data-mode";
import AdminShell from "./components/admin/AdminShell.vue";
import { lastObservationRoute } from "./admin/navigation";
const dataMode = useDataMode();
const adminModeSwitching = ref(false);
const logoutError = ref("");
async function logout() {
  try {
    await post("/auth/logout");
    clearSession();
    await router.push("/connexion");
  } catch (error) {
    logoutError.value = message(error);
  }
}
const expired = () => {
  void router.push("/connexion");
};
onMounted(() => window.addEventListener("auth-expired", expired));
onBeforeUnmount(() => window.removeEventListener("auth-expired", expired));
const route = useRoute();
watch(
  () => dataMode.mode.value,
  () => {
    if (
      dataMode.isDemo.value &&
      /^\/(parcelles\/|videos\/[^/]+\/dossier)/.test(route.path)
    ) {
      void router.replace(
        route.path.startsWith("/parcelles/") ? "/parcelles" : "/videos",
      );
      return;
    }
    if (!route.path.startsWith("/admin")) return;
    adminModeSwitching.value = true;
    void router
      .replace({ path: route.path, query: {}, hash: "" })
      .finally(() => {
        adminModeSwitching.value = false;
      });
  },
  { flush: "sync" },
);
watch(
  () => !!route.meta.designPreview || route.path.startsWith("/admin"),
  (value) => dataMode.setActive(value),
  { immediate: true },
);
watch(
  () => route.fullPath,
  (path, previous) => {
    if (route.meta.designPreview) {
      lastObservationRoute.value = path;
      if (previous?.startsWith("/admin") && dataMode.isReal.value)
        void dataMode.refresh();
    }
  },
  { immediate: true },
);
const open = ref(false);
const sidebar = ref<HTMLElement | null>(null);
const menu = ref<HTMLButtonElement | null>(null);
watch(open, async (visible) => {
  await nextTick();
  if (visible)
    sidebar.value?.querySelector<HTMLAnchorElement>("nav a")?.focus();
  else if (window.matchMedia("(max-width:800px)").matches) menu.value?.focus();
});
const isAdmin = computed(() => route.path.startsWith("/admin"));
const visibleNavigation = computed(() =>
  isAdmin.value ? adminNavigation : navigation,
);
watch(
  () => route.path,
  () => {
    open.value = false;
  },
);
const title = computed(
  () =>
    visibleNavigation.value.find((item) => item.path === route.path)?.label ??
    "Symbiose",
);
</script>
<template>
  <a href="#main-content" class="skip-link">Aller au contenu</a>
  <AppShell v-if="route.meta.designPreview"
    ><RouterView
      :key="`${dataMode.mode.value}:${dataMode.revision.value}:${dataMode.sourceId.value}`"
  /></AppShell>
  <AdminShell
    v-else-if="route.path.startsWith('/admin') && auth.user?.role === 'admin'"
    ><RouterView
      v-if="!adminModeSwitching"
      :key="`${dataMode.mode.value}:${dataMode.sourceId.value}`"
    />
    <p v-else role="status">Changement de source de données…</p></AdminShell
  >
  <main v-else-if="route.meta.public" id="main-content" class="auth-shell">
    <RouterView />
  </main>
  <div v-else-if="auth.user" class="app-shell">
    <aside
      ref="sidebar"
      id="primary-navigation"
      class="sidebar"
      :class="{ 'is-open': open }"
      @keydown.esc="open = false"
    >
      <RouterLink to="/" class="brand" aria-label="Symbiose — accueil"
        ><span class="brand-mark"
          ><i class="pi pi-globe" aria-hidden="true" /></span
        ><span>Symbiose<small>NORMANDIE</small></span></RouterLink
      >
      <span class="nav-label">{{
        isAdmin ? "ADMINISTRATION" : "ESPACE D’OBSERVATION"
      }}</span>
      <nav aria-label="Navigation principale">
        <RouterLink
          v-for="item in visibleNavigation"
          :key="item.path"
          :to="item.path"
          :class="{ selected: route.path === item.path }"
          :aria-current="route.path === item.path ? 'page' : undefined"
          ><i :class="['pi', item.icon]" aria-hidden="true" />{{
            item.label
          }}</RouterLink
        >
        <RouterLink
          v-if="auth.user.role === 'admin'"
          :to="isAdmin ? '/' : '/admin'"
          class="space-switch"
        >
          <i
            :class="['pi', isAdmin ? 'pi-arrow-left' : 'pi-cog']"
            aria-hidden="true"
          />
          {{ isAdmin ? "Espace observation" : "Administration" }}
        </RouterLink>
        <RouterLink to="/profil"><i class="pi pi-user" />Mon profil</RouterLink>
      </nav>
      <div class="sidebar-footer">
        <strong>{{ auth.user.display_name }}</strong
        ><small>{{
          auth.user.role === "admin" ? "Administrateur" : "Client"
        }}</small>
        <button class="account-button" @click="logout">Se déconnecter</button>
        <p v-if="logoutError" role="alert">{{ logoutError }}</p>
      </div>
    </aside>
    <button
      v-if="open"
      class="nav-scrim"
      aria-label="Fermer le menu"
      @click="open = false"
    />
    <div class="workspace">
      <header class="topbar">
        <ModeSelector />
        <button
          class="menu-toggle"
          ref="menu"
          aria-controls="primary-navigation"
          aria-label="Menu de navigation"
          :aria-expanded="open"
          @click="open = !open"
        >
          <i class="pi pi-bars" /></button
        ><span class="breadcrumb"
          >Observatoire <span>/</span> <strong>{{ title }}</strong></span
        ><span class="muted">{{
          isAdmin ? "Gestion et modèles" : "Observer · Analyser · Valider"
        }}</span>
      </header>
      <main id="main-content" tabindex="-1">
        <RouterView v-if="dataMode.isReal.value || route.path === '/profil'" />
        <div v-else class="notice">
          <h1>Espace métier</h1>
          <p>
            Les outils d’administration utilisent des services réels.
            Sélectionnez « Données réelles » pour y accéder avec vos permissions
            habituelles.
          </p>
          <RouterLink to="/">Revenir à la démonstration Symbiose</RouterLink>
        </div>
      </main>
      <footer class="app-footer">
        Symbiose Normandie
        <span>Observation · Validation · Connaissance</span>
      </footer>
    </div>
  </div>
</template>
