<script setup lang="ts">
import { chapters } from "./config";
import {
  pitchChapters,
  pitchIndex,
  pitchSeconds,
  clock,
  chapterProgress,
} from "./pitch";
import { computed } from "vue";
const props = defineProps<{
  progress: number;
  mode: "exploration" | "presentation";
  playing: boolean;
  reducedMotion: boolean;
  fullscreen: boolean;
  fallback?: boolean;
  resumeLabel?: string;
}>();
const emit = defineEmits<{
  seek: [progress: number];
  play: [];
  pause: [];
  mode: [mode: "exploration" | "presentation"];
  fullscreen: [];
  restart: [];
  skip: [];
  resume: [];
  renderer: [];
}>();
const chapterIndex = computed(() => pitchIndex(props.progress));
const seek = (event: Event) =>
  emit("seek", Number((event.target as HTMLInputElement).value) / 100);
</script>
<template>
  <nav class="sx-chapter-nav" aria-label="Environnements du voyage">
    <button
      v-for="(chapter, index) in chapters"
      :key="chapter.id"
      :aria-label="`${index + 1}. ${chapter.name}`"
      :aria-current="chapterIndex === index ? 'step' : undefined"
      @click="emit('seek', chapterProgress(index))"
    >
      <span>0{{ index + 1 }}</span
      ><span class="sx-chapter-name">{{ pitchChapters[index].subject }}</span
      ><i aria-hidden="true" />
    </button>
  </nav>
  <div
    class="sx-presentation-tools"
    role="group"
    aria-label="Commandes du pitch"
  >
    <button
      :disabled="chapterIndex === 0"
      aria-label="Chapitre précédent"
      @click="emit('seek', chapterProgress(chapterIndex - 1))"
    >
      ← <span>Précédent</span>
    </button>
    <button
      :disabled="chapterIndex === 7 && progress >= 0.999"
      aria-label="Chapitre suivant"
      @click="
        emit('seek', chapterIndex === 7 ? 1 : chapterProgress(chapterIndex + 1))
      "
    >
      <span>Suivant</span> →
    </button>
    <button @click="emit('seek', chapterProgress(5))">
      Démonstration <span aria-hidden="true">↗</span>
    </button>
    <button :aria-pressed="fullscreen" @click="emit('fullscreen')">
      {{ fullscreen ? "Quitter le plein écran" : "Plein écran" }}
    </button>
    <details class="sx-recovery-tools">
      <summary>Régie du récit</summary>
      <div>
        <button @click="emit('restart')">Recommencer le récit</button>
        <button @click="emit('skip')">Passer l’animation</button>
        <button v-if="resumeLabel" @click="emit('resume')">
          Reprendre : {{ resumeLabel }}
        </button>
        <button :aria-pressed="fallback" @click="emit('renderer')">
          {{ fallback ? "Réessayer la 3D" : "Secours sans WebGL" }}
        </button>
      </div>
    </details>
  </div>
  <footer class="sx-controls">
    <div class="sx-scroll-cue">
      <span class="sx-scroll-line" aria-hidden="true" /><span>{{
        mode === "presentation"
          ? "Lecture continue · 5 minutes · Espace lecture/pause"
          : "Défilez librement pour explorer"
      }}</span>
    </div>
    <div class="sx-transport">
      <button
        v-if="mode === 'presentation' && !reducedMotion"
        class="sx-play"
        :aria-label="playing ? 'Mettre en pause' : 'Lire le récit'"
        title="Lecture continue jusqu’à 5:00"
        @click="playing ? emit('pause') : emit('play')"
      >
        {{ playing ? "Ⅱ" : "▶" }}
      </button>
      <label class="sx-progress"
        ><span class="sx-sr-only">Position dans le récit</span
        ><input
          type="range"
          min="0"
          max="100"
          step="0.1"
          :value="progress * 100"
          :aria-valuetext="`${clock(pitchSeconds(progress))} sur 5:00, ${pitchChapters[chapterIndex].subject}`"
          @input="seek"
          :style="{ '--sx-progress': `${progress * 100}%` }"
      /></label>
      <span class="sx-counter">{{
        mode === "presentation"
          ? `${clock(pitchSeconds(progress))} / 5:00`
          : `0${chapterIndex + 1} / 08`
      }}</span>
    </div>
    <button
      class="sx-mode"
      :aria-pressed="mode === 'presentation'"
      @click="
        emit('mode', mode === 'exploration' ? 'presentation' : 'exploration')
      "
    >
      <span class="sx-mode-dot" aria-hidden="true" />{{
        mode === "presentation" ? "Mode présentation" : "Mode exploration"
      }}<span aria-hidden="true">⇄</span>
    </button>
  </footer>
</template>
