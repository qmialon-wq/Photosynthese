<script setup lang="ts">
import type { Detection } from "../../data/contracts";
withDefaults(defineProps<{ detections: Detection[]; label?: string }>(), {
  label: "Détections simulées",
});
</script>
<template>
  <div class="sa-detection-overlay" role="img" :aria-label="label">
    <div
      v-for="detection in detections"
      :key="detection.id"
      class="sa-detection"
      :class="{
        'sa-label-align-end':
          detection.bounds.x + detection.bounds.width > 0.85,
      }"
      :data-detection-id="detection.id"
      :style="{
        left: `${detection.bounds.x * 100}%`,
        top: `${detection.bounds.y * 100}%`,
        width: `${detection.bounds.width * 100}%`,
        height: `${detection.bounds.height * 100}%`,
      }"
    >
      <span class="sa-detection-label"
        >{{ detection.label }} ·
        {{
          detection.confidence?.toLocaleString("fr-FR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }) ?? "—"
        }}</span
      >
    </div>
  </div>
</template>
