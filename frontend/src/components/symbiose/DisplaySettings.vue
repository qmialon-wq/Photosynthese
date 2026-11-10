<script setup lang="ts">
import { computed, useId } from "vue";
import { backgroundThemes } from "../../config/background-themes";
import { useWallpaper } from "../../composables/useWallpaper";
import ModeSelector from "./ModeSelector.vue";
const wallpaper = useWallpaper();
const id = useId();
// Reflect the requested choice while loading; a failure restores the last image.
const choice = computed(
  () => wallpaper.pending.value ?? wallpaper.selected.value.id,
);
</script>
<template>
  <h2>Paramètres d’affichage</h2>
  <div class="sym-display-settings-body">
    <ModeSelector visible-label />
    <label class="sym-setting-toggle">
      <input
        type="checkbox"
        :checked="wallpaper.reduceMotion.value"
        @change="
          wallpaper.setReduceMotion(($event.target as HTMLInputElement).checked)
        "
      />
      Réduire les animations
    </label>
    <fieldset
      class="sym-wallpaper-picker"
      :aria-describedby="`${id}-description`"
    >
      <legend>Fond d’écran</legend>
      <p :id="`${id}-description`">
        Personnalisez votre environnement naturel.
      </p>
      <div class="sym-wallpaper-grid">
        <label
          v-for="theme in backgroundThemes"
          :key="theme.id"
          class="sym-wallpaper-card"
          :class="{ 'is-selected': choice === theme.id }"
          :aria-busy="wallpaper.pending.value === theme.id"
        >
          <input
            type="radio"
            :name="`${id}-wallpaper`"
            :value="theme.id"
            :checked="choice === theme.id"
            :aria-label="theme.name"
            :aria-describedby="`${id}-${theme.id}`"
            @change="wallpaper.setTheme(theme.id)"
          />
          <img
            :src="theme.thumbnail"
            alt=""
            width="320"
            height="180"
            loading="lazy"
            decoding="async"
          />
          <span class="sym-wallpaper-name"
            >{{ theme.name
            }}<span
              v-if="choice === theme.id"
              class="sym-wallpaper-check"
              aria-hidden="true"
              >✓</span
            ></span
          >
          <span :id="`${id}-${theme.id}`" class="sym-sr-only">{{
            theme.description
          }}</span>
        </label>
      </div>
    </fieldset>
    <p class="sym-wallpaper-status" role="status" aria-live="polite">
      {{
        wallpaper.error.value ||
        (wallpaper.pending.value
          ? "Chargement du fond…"
          : `Fond sélectionné : ${wallpaper.selected.value.name}.`)
      }}
    </p>
    <p class="sym-wallpaper-credit">
      <a
        v-if="wallpaper.selected.value.source"
        :href="wallpaper.selected.value.source"
        target="_blank"
        rel="noopener noreferrer"
        >Photo : {{ wallpaper.selected.value.credit }} / Unsplash</a
      >
      <span v-else>{{ wallpaper.selected.value.credit }}</span>
    </p>
    <button class="sym-wallpaper-reset" @click="wallpaper.reset">
      Restaurer le fond par défaut
    </button>
  </div>
</template>
