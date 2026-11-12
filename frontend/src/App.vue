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
import WallpaperBackground from "./components/symbiose/WallpaperBackground.vue";
import AppearanceMenu from "./components/symbiose/AppearanceMenu.vue";
import { useDataMode } from "./data/data-mode";
import AdminShell from "./components/admin/AdminShell.vue";
import { lastObservationRoute } from "./admin/navigation";
import { useEnvironmentTheme } from "./composables/useEnvironmentTheme";
import LoginTransition from "./components/symbiose/LoginTransition.vue";
import LandingPage from "./pages/LandingPage.vue";
import ClientGuide from "./components/ClientGuide.vue";
import HelpButton from "./components/HelpButton.vue";
useEnvironmentTheme();
const dataMode = useDataMode();

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
const observation = computed(
  () => route.meta.observation || (route.meta.home && !!auth.user),
);
watch(
  () => ["/videos", "/parcelles"].includes(route.path),
  (value) => dataMode.setActive(value),
  { immediate: true },
);
watch(
  () => route.fullPath,
  (path, previous) => {
    if (observation.value) {
      lastObservationRoute.value = path;
      if (previous?.startsWith("/admin")) void dataMode.refresh();
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
  <LoginTransition />
  <ClientGuide />
  <a href="#main-content" class="skip-link">Aller au contenu</a>
  <LandingPage v-if="route.meta.home && !auth.user" />
  <AppShell v-else-if="observation && auth.user"
    ><div
      :class="{
        'adm-content sym-operational-page': [
          '/',
          '/analyses',
          '/review',
          '/documents',
        ].includes(route.path),
      }"
    >
      <RouterView
        :key="`${dataMode.revision.value}:${dataMode.sourceId.value}`"
      /></div
  ></AppShell>
  <AdminShell
    v-else-if="route.path.startsWith('/admin') && auth.user?.role === 'admin'"
    ><RouterView :key="`${dataMode.sourceId.value}`" />
  </AdminShell>
  <main v-else-if="route.meta.public" id="main-content" class="auth-shell">
    <RouterView />
  </main>
  <div v-else-if="auth.user" class="app-shell app-wallpaper-shell">
    <WallpaperBackground />
    <AppearanceMenu class="legacy-appearance-menu" @open="open = false" />
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
        <HelpButton />
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
        <RouterView />
      </main>
      <footer class="app-footer">
        Symbiose Normandie
        <span>Observation · Validation · Connaissance</span>
      </footer>
    </div>
  </div>
</template>
