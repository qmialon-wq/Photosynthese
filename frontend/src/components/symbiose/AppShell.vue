<script setup lang="ts">
import { nextTick, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, ApiError, message, post } from "../../api";
import {
  auth,
  acceptSession,
  clearSession,
  type Session,
} from "../../auth-state";
import logo from "../../assets/symbiose-logo.png";
import WheelNavigation from "./WheelNavigation.vue";
import SymIcon from "./SymIcon.vue";
import DisplaySettings from "./DisplaySettings.vue";
import WallpaperBackground from "./WallpaperBackground.vue";
import { useWallpaper } from "../../composables/useWallpaper";
import { useDataMode } from "../../data/data-mode";
const dataMode = useDataMode();
const route = useRoute();
const router = useRouter();
const scrolled = ref(false);
const updateScroll = () => { scrolled.value = window.scrollY > 0; };
onMounted(() => {
  updateScroll();
  window.addEventListener("scroll", updateScroll, { passive: true });
});
onBeforeUnmount(() => window.removeEventListener("scroll", updateScroll));
const logoutBusy = ref(false);
const logoutError = ref("");
async function logout() {
  if (logoutBusy.value) return;
  logoutBusy.value = true;
  logoutError.value = "";
  try {
    try {
      // Une page rechargée peut encore avoir le cookie sans le jeton CSRF en mémoire.
      if (!auth.csrf) acceptSession(await api<Session>("/auth/me"));
      await post("/auth/logout");
    } catch (error) {
      // Une session déjà expirée permet aussi de revenir à la connexion.
      if (!(error instanceof ApiError && error.status === 401)) throw error;
    }
    clearSession();
    await router.replace("/connexion");
  } catch (error) {
    logoutError.value = message(error);
  } finally {
    logoutBusy.value = false;
  }
}
const panel = ref<
  "notifications" | "profile" | "settings" | "settings-menu" | null
>(null);
const wallpaper = useWallpaper();
const reduceMotion = wallpaper.reduceMotion;
const actionButtons = ref<HTMLButtonElement[]>([]);
const settingsButton = ref<HTMLButtonElement>();
const verifiedAdmin = ref(false);
async function openSettingsMenu() {
  panel.value = panel.value === "settings-menu" ? null : "settings-menu";
  if (!panel.value) return;
  verifiedAdmin.value = false;
  try {
    acceptSession(await api<Session>("/auth/me"));
    verifiedAdmin.value = auth.user?.role === "admin";
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) clearSession();
  }
}
const actions = [
  { key: "notifications", label: "Notifications", icon: "bell" },
  { key: "profile", label: "Mon profil", icon: "user" },
] as const;
watch(
  () => route.path,
  () => {
    panel.value = null;
  },
);
function togglePanel(value: NonNullable<typeof panel.value>) {
  panel.value = panel.value === value ? null : value;
}
watch(panel, async (value) => {
  if (value !== "settings") return;
  await nextTick();
  document
    .querySelector<HTMLSelectElement>("#sym-action-panel select")
    ?.focus();
});
function closePanel() {
  const previous = panel.value;
  if (!previous) return;
  panel.value = null;
  if (previous === "settings" || previous === "settings-menu")
    settingsButton.value?.focus();
  else actionButtons.value[previous === "notifications" ? 0 : 1]?.focus();
}
</script>
<template>
  <div
    class="symbiose-shell"
    :class="{ 'sym-reduced-motion': reduceMotion }"
    @keydown.esc="closePanel"
  >
    <div class="sym-canvas">
      <WallpaperBackground />
      <header class="sym-header">
        <RouterLink
          to="/"
          class="sym-brand"
          aria-label="Symbiose Normandie — accueil"
          ><img :src="logo" alt="Symbiose" width="3634" height="1242" /><span
            >NORMANDIE</span
          ></RouterLink
        >
        <div class="sym-header-actions" :class="{ 'is-scrolled': scrolled }" aria-label="Actions du compte">
          <button
            v-for="(action, i) in actions"
            :key="action.key"
            :ref="
              (el) => {
                if (el) actionButtons[i] = el as HTMLButtonElement;
              }
            "
            class="sym-circle-button"
            :aria-label="action.label"
            :aria-expanded="panel === action.key"
            aria-controls="sym-action-panel"
            @click="togglePanel(action.key)"
          >
            <SymIcon :name="action.icon" :size="25" /><span
              v-if="
                action.key === 'notifications' &&
                dataMode.capabilities.value.simulate
              "
              class="sym-notification-dot"
              aria-hidden="true"
            />
          </button>
        </div>
      </header>
      <WheelNavigation :reduced-motion="reduceMotion" />
      <button
        ref="settingsButton"
        class="sym-circle-button sym-settings"
        aria-label="Paramètres"
        :aria-expanded="panel === 'settings' || panel === 'settings-menu'"
        aria-controls="sym-action-panel"
        @click="openSettingsMenu"
      >
        <SymIcon name="settings" :size="29" />
      </button>
      <aside
        v-if="panel"
        id="sym-action-panel"
        class="sym-glass sym-action-panel"
        :class="{
          'sym-display-settings-panel': panel === 'settings',
          'sym-settings-panel':
            panel === 'settings' || panel === 'settings-menu',
        }"
        :aria-label="
          panel === 'settings' || panel === 'settings-menu'
            ? 'Paramètres d’affichage'
            : panel === 'profile'
              ? 'Mon profil'
              : 'Notifications'
        "
      >
        <button class="sym-close" aria-label="Fermer" @click="closePanel">
          <SymIcon name="close" :size="20" />
        </button>
        <div
          v-if="panel === 'settings-menu'"
          class="sym-settings-menu"
          aria-label="Paramètres et administration"
        >
          <h2>Votre espace</h2>
          <button @click="panel = 'settings'">
            <SymIcon name="sliders" :size="21" />Paramètres d’affichage
          </button>
          <RouterLink
            v-if="verifiedAdmin && auth.user?.role === 'admin'"
            to="/admin"
            ><SymIcon name="settings" :size="21" />Administration</RouterLink
          >
        </div>
        <DisplaySettings v-else-if="panel === 'settings'" />
        <template v-else-if="panel === 'profile'"
          ><h2>Votre espace Symbiose</h2>
          <p>
            {{
              auth.user?.display_name ||
              (dataMode.isDemo.value
                ? "Profil de démonstration"
                : "Session non connectée")
            }}
          </p>
          <p v-if="!auth.user">
            {{
              dataMode.isDemo.value
                ? "Données de démonstration locales, sans serveur."
                : "Connectez-vous pour consulter les données enregistrées."
            }}
          </p>
          <button
            class="sym-profile-logout"
            :disabled="logoutBusy"
            :aria-busy="logoutBusy"
            @click="logout"
          >
            {{ logoutBusy ? "Déconnexion en cours…" : "Se déconnecter" }}
          </button>
          <p v-if="logoutError" class="sym-logout-error" role="alert">
            {{ logoutError }}
          </p></template
        >
        <template v-else
          ><h2>Notifications</h2>
          <p>Notifications non connectées.</p></template
        >
      </aside>
      <main id="main-content" class="sym-main" tabindex="-1"><slot /></main>
      <span class="sym-demo-note">{{
        dataMode.isDemo.value
          ? "Mode démonstration · données fictives"
          : "Données réelles · lecture seule"
      }}</span>
    </div>
  </div>
</template>
