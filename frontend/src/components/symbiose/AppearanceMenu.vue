<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { auth } from "../../auth-state";
import DisplaySettings from "./DisplaySettings.vue";
import SymIcon from "./SymIcon.vue";
const emit = defineEmits<{ open: [] }>();
const route = useRoute();
const panel = ref<"menu" | "settings" | null>(null);
const button = ref<HTMLButtonElement>();
const content = ref<HTMLElement>();
function close() {
  panel.value = null;
  button.value?.focus();
}
function toggle() {
  panel.value = panel.value ? null : "menu";
  if (panel.value) emit("open");
}
watch(
  () => route.path,
  () => {
    panel.value = null;
  },
);
watch(panel, async (value) => {
  if (!value) return;
  await nextTick();
  content.value
    ?.querySelector<HTMLElement>(
      value === "settings" ? "input" : ".sym-settings-menu button",
    )
    ?.focus();
});
</script>
<template>
  <div class="symbiose-shell sym-appearance-menu" @keydown.esc.stop="close">
    <button
      ref="button"
      class="sym-circle-button sym-settings"
      aria-label="Paramètres"
      :aria-expanded="!!panel"
      aria-controls="appearance-panel"
      @click="toggle"
    >
      <SymIcon name="settings" :size="29" />
    </button>
    <aside
      v-if="panel"
      id="appearance-panel"
      ref="content"
      class="sym-glass sym-action-panel sym-settings-panel"
      :class="{ 'sym-display-settings-panel': panel === 'settings' }"
      aria-label="Paramètres d’affichage"
    >
      <button class="sym-close" aria-label="Fermer" @click="close">
        <SymIcon name="close" :size="20" />
      </button>
      <DisplaySettings v-if="panel === 'settings'" />
      <div v-else class="sym-settings-menu">
        <h2>Votre espace</h2>
        <button @click="panel = 'settings'">
          <SymIcon name="sliders" :size="21" />Paramètres d’affichage
        </button>
        <RouterLink v-if="auth.user?.role === 'admin'" to="/admin"
          ><SymIcon name="settings" :size="21" />Administration</RouterLink
        >
      </div>
    </aside>
  </div>
</template>
