<script setup lang="ts">
import type { AnimalBox } from "./world-fauna";
import { computed } from "vue";
import { layoutAnimalLabels } from "./animal-labels";
const props = defineProps<{ animals: AnimalBox[] }>();
const labels = computed(() => layoutAnimalLabels(props.animals));
</script>
<template>
  <div class="sx-fauna-annotations" aria-label="Animaux 3D illustratifs">
    <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
      <line
        v-for="a in labels"
        :key="a.id"
        :x1="(a.x + a.width / 2) * 1000"
        :y1="a.y * 1000"
        :x2="a.labelX * 1000 + 12"
        :y2="a.labelY * 1000 + 24"
      />
    </svg>
    <div
      v-for="animal in labels"
      :key="animal.id"
      class="sx-animal-box"
      :data-animal="animal.id"
      :style="{
        left: `${animal.x * 100}%`,
        top: `${animal.y * 100}%`,
        width: `${animal.width * 100}%`,
        height: `${animal.height * 100}%`,
        opacity: animal.opacity,
      }"
    ></div>
    <span
      v-for="animal in labels"
      :key="animal.id + '-label'"
      class="sx-animal-label"
      :style="{
        left: `${animal.labelX * 100}%`,
        top: `${animal.labelY * 100}%`,
        opacity: animal.opacity,
      }"
      >{{ animal.label }}</span
    >
    <p class="sx-fauna-note">
      Animaux 3D illustratifs · identifications non calculées
    </p>
  </div>
</template>
<style>
.sx-experience .sx-fauna-annotations {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}
.sx-experience .sx-animal-box {
  position: absolute;
  border: 1px solid #c7f5a9b0;
  box-shadow: 0 0 0 1px #09201755;
}
.sx-experience .sx-animal-label {
  position: absolute;
  max-width: 210px;
  padding: 3px 7px;
  background: #0b241cf2;
  color: #edf7e4;
  border-left: 2px solid #b9ef84;
  font:
    11px/1.4 "Segoe UI",
    sans-serif;
}
.sx-experience .sx-fauna-annotations > svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  stroke: #c7f5a970;
  stroke-width: 0.6;
}
.sx-experience .sx-fauna-note {
  position: absolute;
  bottom: 176px;
  right: var(--sx-gutter);
  margin: 0;
  color: #edf7e4;
  background: #0b241cdd;
  padding: 4px 7px;
  font-size: 9px;
}
@media (max-width: 600px) {
  .sx-experience .sx-animal-label {
    font-size: 9px;
    max-width: 120px;
  }
  .sx-experience .sx-fauna-note {
    bottom: 140px;
    font-size: 8px;
    max-width: 190px;
  }
}
</style>
