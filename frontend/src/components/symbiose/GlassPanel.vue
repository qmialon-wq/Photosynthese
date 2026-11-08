<script setup lang="ts">
import TopographicPattern from "./TopographicPattern.vue";
withDefaults(defineProps<{ as?: string; topography?: boolean }>(), {
  as: "section",
  topography: false,
});
</script>
<template>
  <component :is="as" class="sym-glass"
    ><TopographicPattern v-if="topography" /><slot
  /></component>
</template>
