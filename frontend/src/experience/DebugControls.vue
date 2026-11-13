<script setup lang="ts">
import { computed, ref } from "vue";
import {
  transitions,
  clamp01,
  transitionProgress,
  type TransitionId,
  type JourneyLayers,
} from "./journey";
import { narrativeDuration } from "./config";
import { sampleCamera } from "./CameraController";
import type { FrameReport } from "./telemetry";
import type { PerformanceSample } from "./PerformanceMonitor";
const props = defineProps<{
  progress: number;
  layers: JourneyLayers;
  frame?: FrameReport;
  performance?: PerformanceSample;
  issues: string[];
  fallback: boolean;
}>();
const emit = defineEmits<{
  seek: [progress: number];
  layer: [key: keyof JourneyLayers, value: boolean];
}>();
const queryTransition = new URLSearchParams(location.search).get("transition");
const selected = ref<TransitionId>(
  transitions.find((t) => t.id === queryTransition)?.id ?? "ascent",
);
const current = computed(() => {
  const spec = transitions.find((t) => t.id === selected.value)!;
  return {
    ...spec,
    local: clamp01(
      (props.progress * narrativeDuration - spec.start) /
        (spec.end - spec.start),
    ),
  };
});
const pose = computed(() => props.frame ?? sampleCamera(props.progress));
const labels: Record<keyof JourneyLayers, string> = {
  terrain: "Relief / falaises",
  vegetation: "Végétation / calques alpha",
  water: "Eau / réfraction",
  atmosphere: "Ciel / brume / lumière",
  cartography: "Tracés illustratifs",
  observation: "Animal / capteurs / cadre",
  particles: "Bulles / données / logo",
  reference: "Référence générée (fixe)",
};
function select(event: Event) {
  selected.value = (event.target as HTMLSelectElement).value as TransitionId;
  emit("seek", transitionProgress(selected.value, 0));
}
function scrub(event: Event) {
  emit(
    "seek",
    transitionProgress(
      current.value.id,
      Number((event.target as HTMLInputElement).value),
    ),
  );
}
</script>
<template>
  <details class="sx-debug-panel" open>
    <summary>DEBUG · transitions</summary>
    <div class="sx-debug-body">
      <label
        >Transition<select
          aria-label="Transition à inspecter"
          :value="current.id"
          @change="select"
        >
          <option
            v-for="transition in transitions"
            :key="transition.id"
            :value="transition.id"
            :data-start="transition.start"
            :data-end="transition.end"
          >
            {{ transition.index + 1 }}. {{ transition.name }}
          </option>
        </select></label
      >
      <label
        >Progression locale · {{ (current.local * 100).toFixed(1) }} %<input
          aria-label="Progression de la transition"
          type="range"
          min="0"
          max="1"
          step="0.001"
          :value="current.local"
          @input="scrub"
      /></label>
      <div class="sx-debug-stops">
        <button
          v-for="p in [0, 0.25, 0.5, 0.75, 1]"
          :key="p"
          @click="emit('seek', transitionProgress(current.id, p))"
        >
          {{ p * 100 }} %
        </button>
      </div>
      <fieldset>
        <legend>Couches</legend>
        <label v-for="(label, key) in labels" :key="key"
          ><input
            type="checkbox"
            :disabled="fallback && key !== 'reference'"
            :checked="layers[key]"
            @change="
              emit('layer', key, ($event.target as HTMLInputElement).checked)
            "
          />{{ label }}</label
        >
      </fieldset>
      <output aria-label="Caméra inspectée"
        >Position {{ pose.position.map((n) => n.toFixed(2)).join(" / ")
        }}<br />Cible {{ pose.target.map((n) => n.toFixed(2)).join(" / ")
        }}<br />Champ {{ pose.fov.toFixed(1) }}° · global
        {{ progress.toFixed(5) }}</output
      >
      <output aria-label="Performances mesurées"
        >{{
          performance
            ? `${performance.fps} fps · ${performance.frameMs} ms`
            : "Mesure pendant le déplacement"
        }}<br />{{
          frame
            ? `${frame.drawCalls} appels · ${frame.triangles} triangles · DPR ${frame.pixelRatio} · ${frame.quality}`
            : ""
        }}</output
      >
      <p v-if="fallback">
        Version simplifiée 2D · masques spatiaux, caméra inspectée théorique.
      </p>
      <p v-if="issues.length" role="status">
        Calques indisponibles : {{ issues.join(", ") }}. Géométrie conservée.
      </p>
      <p class="sx-debug-notice">
        Reconstruction d’intention, géographie et signaux illustratifs. Les
        fonds propres et profondeurs calibrées restent absents.
      </p>
    </div>
  </details>
</template>
