<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, ApiError, message, post } from "../../api";
import {
  auth,
  acceptSession,
  clearSession,
  type Session,
} from "../../auth-state";
import logo from "../../assets/symbiose-logo.png";
import { symbioseNavigation } from "../../symbiose-navigation";
import WheelNavigation from "./WheelNavigation.vue";
import SymIcon from "./SymIcon.vue";
import ModeSelector from "./ModeSelector.vue";
import { useDataMode } from "../../data/data-mode";
const dataMode = useDataMode();
const route = useRoute();
const router = useRouter();
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
const panel = ref<"search" | "notifications" | "profile" | "settings" | null>(
  null,
);
const query = ref("");
const reduceMotion = ref(false);
const searchField = ref<HTMLInputElement>();
const actionButtons = ref<HTMLButtonElement[]>([]);
const settingsButton = ref<HTMLButtonElement>();
const actions = [
  { key: "search", label: "Rechercher", icon: "search" },
  { key: "notifications", label: "Notifications", icon: "bell" },
  { key: "profile", label: "Mon profil", icon: "user" },
] as const;
const results = computed(() =>
  symbioseNavigation.filter((item) =>
    item.label
      .toLocaleLowerCase("fr")
      .includes(query.value.toLocaleLowerCase("fr")),
  ),
);
watch(
  () => route.path,
  () => {
    panel.value = null;
    query.value = "";
  },
);
async function togglePanel(value: NonNullable<typeof panel.value>) {
  panel.value = panel.value === value ? null : value;
  if (value === "search" && panel.value) {
    await nextTick();
    searchField.value?.focus();
  }
}
function closePanel() {
  const previous = panel.value;
  if (!previous) return;
  panel.value = null;
  if (previous === "settings") settingsButton.value?.focus();
  else
    actionButtons.value[
      previous === "search" ? 0 : previous === "notifications" ? 1 : 2
    ]?.focus();
}
</script>
<template>
  <div
    class="symbiose-shell"
    :class="{ 'sym-reduced-motion': reduceMotion }"
    @keydown.esc="closePanel"
  >
    <div class="sym-canvas">
      <div class="sym-forest" aria-hidden="true" />
      <header class="sym-header">
        <RouterLink
          to="/"
          class="sym-brand"
          aria-label="Symbiose Normandie — accueil"
          ><img :src="logo" alt="Symbiose" width="3634" height="1242" /><span
            >NORMANDIE</span
          ></RouterLink
        >
        <div class="sym-header-actions" aria-label="Actions du compte">
          <ModeSelector />
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
              v-if="action.key === 'notifications' && dataMode.capabilities.value.simulate"
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
        :aria-expanded="panel === 'settings'"
        aria-controls="sym-action-panel"
        @click="togglePanel('settings')"
      >
        <SymIcon name="settings" :size="29" />
      </button>
      <aside
        v-if="panel"
        id="sym-action-panel"
        class="sym-glass sym-action-panel"
        :class="{ 'sym-settings-panel': panel === 'settings' }"
        :aria-label="
          panel === 'search'
            ? 'Recherche dans les rubriques'
            : panel === 'settings'
              ? 'Paramètres d’affichage'
              : panel === 'profile'
                ? 'Mon profil'
                : 'Notifications'
        "
      >
        <button class="sym-close" aria-label="Fermer" @click="closePanel">
          <SymIcon name="close" :size="20" />
        </button>
        <template v-if="panel === 'search'"
          ><h2>Rechercher une rubrique</h2>
          <label for="sym-search">Nom de la rubrique</label
          ><input
            id="sym-search"
            ref="searchField"
            v-model="query"
            type="search"
            autocomplete="off"
            placeholder="Vidéothèque, analyses…"
          />
          <ul>
            <li v-for="item in results" :key="item.path">
              <RouterLink :to="item.path"
                >{{ item.label }}<SymIcon name="arrow" :size="18"
              /></RouterLink>
            </li>
          </ul>
          <p v-if="!results.length">Aucune rubrique trouvée.</p></template
        >
        <template v-else-if="panel === 'settings'"
          ><h2>Paramètres d’affichage</h2>
          <label class="sym-setting-toggle"
            ><input v-model="reduceMotion" type="checkbox" />Réduire les
            animations</label
          >
          <p>Les préférences s’appliquent à cet aperçu.</p></template
        >
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
