<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { auth, clearSession } from "../../auth-state";
import { message, post } from "../../api";
import { useDataMode } from "../../data/data-mode";
import { adminSections } from "../../admin/navigation";
import { closeAdminConfirmation } from "../../admin/confirmation";
import AdminNavigation from "./AdminNavigation.vue";
import AdminConfirmation from "./AdminConfirmation.vue";
import WallpaperBackground from "../symbiose/WallpaperBackground.vue";
import AppearanceMenu from "../symbiose/AppearanceMenu.vue";
import { useWallpaper } from "../../composables/useWallpaper";
const wallpaper = useWallpaper();
import SymIcon from "../symbiose/SymIcon.vue";
import logo from "../../assets/symbiose-logo.png";
const store = useDataMode(),
  route = useRoute(),
  router = useRouter();
const open = ref(false),
  menu = ref<HTMLButtonElement>(),
  aside = ref<HTMLElement>();
const mobileQuery = matchMedia("(max-width:1000px)");
const narrow = ref(mobileQuery.matches);
function resizeNavigation() {
  narrow.value = mobileQuery.matches;
  if (!narrow.value) open.value = false;
}
mobileQuery.addEventListener("change", resizeNavigation);
onBeforeUnmount(() =>
  mobileQuery.removeEventListener("change", resizeNavigation),
);
function trapNavigation(event: KeyboardEvent) {
  if (!open.value || !narrow.value) return;
  const items = Array.from(
    aside.value?.querySelectorAll<HTMLElement>("a, button:not(:disabled)") ||
      [],
  );
  const first = items[0],
    last = items.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last?.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first?.focus();
  }
}
const error = ref(""),
  busy = ref(false);
const title = computed(
  () =>
    adminSections.find((section) => section.path === route.path)?.label ||
    "Administration",
);
watch(
  () => route.path,
  () => {
    open.value = false;
    closeAdminConfirmation();
  },
);
watch(() => store.mode.value, closeAdminConfirmation);
watch(open, async (value) => {
  await nextTick();
  if (value) aside.value?.querySelector<HTMLAnchorElement>("nav a")?.focus();
  else if (matchMedia("(max-width:1000px)").matches) menu.value?.focus();
});
onBeforeUnmount(closeAdminConfirmation);
async function logout() {
  busy.value = true;
  error.value = "";
  try {
    await post("/auth/logout");
    clearSession();
    await router.replace("/connexion");
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div
    class="symbiose-shell adm-shell"
    :class="{ 'sym-reduced-motion': wallpaper.reduceMotion.value }"
  >
    <WallpaperBackground />
    <aside
      ref="aside"
      id="admin-navigation"
      class="sym-glass adm-sidebar"
      :class="{ 'is-open': open }"
      :inert="narrow && !open"
      @keydown.tab="trapNavigation"
      @keydown.esc="open = false"
    >
      <button
        v-if="narrow"
        class="sym-circle-button adm-nav-close"
        aria-label="Fermer le menu administratif"
        @click="open = false"
      >
        <SymIcon name="close" :size="18" />
      </button>
      <RouterLink
        to="/admin"
        class="adm-brand"
        aria-label="Symbiose — administration"
        ><img :src="logo" alt="Symbiose" width="3634" height="1242" /><span
          >NORMANDIE</span
        ></RouterLink
      >
      <p class="sym-eyebrow adm-nav-label">ESPACE ADMINISTRATION</p>
      <AdminNavigation @navigate="open = false" />
      <div class="adm-account">
        <SymIcon name="user" :size="23" />
        <div>
          <strong>{{ auth.user?.display_name }}</strong
          ><small>Administrateur</small>
        </div>
        <button class="sv-button-quiet" :disabled="busy" @click="logout">
          {{ busy ? "Déconnexion…" : "Se déconnecter" }}
        </button>
        <p v-if="error" role="alert">{{ error }}</p>
      </div>
    </aside>
    <button
      v-if="open"
      class="adm-scrim"
      aria-label="Fermer la navigation administrative"
      @click="open = false"
    />
    <div class="adm-workspace">
      <header class="sym-glass adm-header">
        <button
          ref="menu"
          class="sym-circle-button adm-menu"
          aria-label="Navigation administrative"
          aria-controls="admin-navigation"
          :aria-expanded="open"
          @click="open = !open"
        >
          <SymIcon name="menu" :size="23" />
        </button>
        <div class="adm-breadcrumb">
          <span>Administration</span
          ><SymIcon name="chevron" :size="14" /><strong>{{ title }}</strong>
        </div>
        <div class="adm-header-actions">
          <RouterLink
            class="sym-circle-button"
            to="/profil"
            aria-label="Mon profil"
            ><SymIcon name="user" :size="23"
          /></RouterLink>
        </div>
      </header>
      <p class="adm-mode-note" role="status">
        {{
          store.isDemo.value
            ? "Mode démonstration · données fictives et actions locales. Aucun compte ni worker réel n’est modifié."
            : "Données réelles · services authentifiés. Les modifications sensibles demandent une confirmation."
        }}
      </p>
      <main id="main-content" class="adm-content" tabindex="-1"><slot /></main>
      <footer class="adm-footer">
        <span>Symbiose Normandie</span
        ><span>Administration · Données · Modèles</span>
      </footer>
    </div>
    <AppearanceMenu class="adm-appearance-menu" @open="open = false" />
    <AdminConfirmation />
  </div>
</template>
