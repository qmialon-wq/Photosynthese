<script setup lang="ts">
import TopographicPattern from "./TopographicPattern.vue";
withDefaults(
  defineProps<{
    as?: string;
    topography?: boolean;
    depth?: "panel" | "page" | "card" | "inset";
  }>(),
  {
    as: "section",
    topography: false,
    depth: "panel",
  },
);
</script>
<template>
  <component :is="as" class="sym-glass" :class="`sym-glass-${depth}`"
    ><TopographicPattern v-if="topography" /><slot
  /></component>
</template>
