<script setup lang="ts">
import { playbackTime } from "../../data/analysis-preview";
import {
  observationSpeciesLabel,
  type DemoObservation,
} from "../../data/observation-preview";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
import StatusBadge from "./StatusBadge.vue";
defineProps<{ observation: DemoObservation; selected: boolean }>();
const emit = defineEmits<{
  toggle: [id: string];
  preview: [observation: DemoObservation];
}>();
function thumbnailFrame(event: Event) {
  const video = event.target as HTMLVideoElement;
  if (Number.isFinite(video.duration))
    video.currentTime = Math.min(1.5, video.duration / 4);
}
</script>
<template>
  <GlassPanel
    as="article"
    class="sr-observation"
    :class="{ 'is-selected': selected, 'is-protected': observation.protected }"
    :data-observation-id="observation.id"
    :aria-labelledby="`${observation.id}-title`"
  >
    <label
      class="sr-observation-select"
      :title="
        observation.protected
          ? 'Image de test protégée : sélection et modification indisponibles.'
          : undefined
      "
      ><input
        type="checkbox"
        :checked="selected"
        :disabled="observation.protected"
        :aria-label="`Sélectionner l’observation ${observation.number}`"
        :aria-describedby="
          observation.protected ? `${observation.id}-protection` : undefined
        "
        @change="emit('toggle', observation.id)"
      /><span>{{
        observation.protected ? "Test protégé" : "Sélectionner"
      }}</span
      ><span
        v-if="observation.protected"
        :id="`${observation.id}-protection`"
        class="sym-sr-only"
        >Image de test protégée. Cette observation ne peut être ni validée ni
        retirée.</span
      ></label
    >
    <button
      class="sr-observation-preview"
      :aria-label="`Prévisualiser l’observation ${observation.number} : ${observation.filename}`"
      @click="emit('preview', observation)"
    >
      <video
        v-if="observation.media.kind === 'video'"
        :src="observation.media.source"
        preload="metadata"
        @loadedmetadata="thumbnailFrame"
        muted
        playsinline
        aria-hidden="true"
        tabindex="-1"
      />
      <span
        v-else
        class="sr-observation-photo"
        :style="{
          backgroundImage: `url(${observation.media.poster})`,
          backgroundSize: observation.media.posterSize || 'cover',
          backgroundPosition: observation.media.posterPosition || 'center',
        }"
      />
      <span class="sv-play-button"
        ><svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m8 4 12 8-12 8Z" /></svg></span
      ><span class="sv-duration"
        ><SymIcon name="video" :size="12" />{{
          playbackTime(observation.media.duration).padStart(5, "0")
        }}</span
      >
    </button>
    <h2 :id="`${observation.id}-title`" class="sr-observation-species">
      {{
        observationSpeciesLabel(
          observation.assignedSpecies || observation.suggestedSpecies,
        )
      }}
    </h2>
    <p class="sr-observation-filename" :title="observation.filename">
      {{ observation.filename }}
    </p>
    <div class="sr-observation-meta">
      <StatusBadge
        v-if="observation.status === 'validated'"
        status="validated"
        label="Validée"
      /><span v-else class="sr-review-status"
        ><SymIcon name="info" :size="15" />À revoir</span
      ><span>{{ observation.context }}</span>
    </div>
  </GlassPanel>
</template>
