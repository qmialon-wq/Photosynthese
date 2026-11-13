<script setup lang="ts">
import { computed } from "vue";
import type { FrameReport } from "./telemetry";
const props = defineProps<{ frame?: FrameReport; visible: boolean }>();
const rectangle = computed(() => {
  const f = props.frame;
  if (!f) return {};
  const t = f.dataMorph,
    b = f.bounds;
  const x = Math.min(0.85, Math.max(0.05, b.x)),
    y = Math.min(0.8, Math.max(0.12, b.y)),
    w = Math.min(0.5, Math.max(0.055, b.width)),
    h = Math.min(0.5, Math.max(0.08, b.height));
  return {
    left: `${(x + (0.62 - x) * t) * 100}%`,
    top: `${(y + (0.31 - y) * t) * 100}%`,
    width: `${(w + (0.3 - w) * t) * 100}%`,
    height: `${(h + (0.27 - h) * t) * 100}%`,
    opacity: f.observation,
  };
});
</script>
<template>
  <div
    v-if="visible && frame && frame.observation > 0.01"
    class="sx-detection"
    :style="rectangle"
  >
    <p>ILLUSTRATION PÉDAGOGIQUE</p>
    <strong>Chevreuil · identification candidate</strong
    ><span>Confiance : non calculée</span>
    <ol v-if="frame.dataMorph > 0.45">
      <li>Observation du milieu</li>
      <li>Proposition à examiner</li>
      <li>Validation humaine requise</li>
    </ol>
  </div>
  <div
    v-if="frame && frame.logo > 0.01"
    class="sx-logo-conclusion"
    :style="{ opacity: frame.logo }"
  >
    <img
      src="/experience-art/shared/symbiose-logo.png"
      alt="Symbiose"
      width="3634"
      height="1242"
    />
    <p>
      Les liens du récit convergent.<br />Particules illustratives · aucune
      mesure de terrain.
    </p>
    <RouterLink class="sx-cta" to="/inscription"
      >Commencer mes observations ↗</RouterLink
    >
  </div>
</template>
