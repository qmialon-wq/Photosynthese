<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  pitchChapters,
  pitchIndex,
  statusLabels,
  clock,
  appUrl,
} from "./pitch";
import PitchVisual from "./PitchVisual.vue";
import DemoVideo from "./DemoVideo.vue";
const props = withDefaults(
  defineProps<{
    progress: number;
    reducedMotion: boolean;
    suspended: boolean;
    appHref?: string;
  }>(),
  { appHref: appUrl },
);
defineEmits<{ begin: []; sources: []; videoPlaying: [] }>();
const chapter = computed(() => pitchChapters[pitchIndex(props.progress)]);
const content = ref<HTMLElement>();
watch(
  () => chapter.value.id,
  () => {
    if (content.value) content.value.scrollTop = 0;
  },
  { flush: "post" },
);
</script>

<template>
  <div ref="content" class="sx-pitch-content" :data-chapter="chapter.id">
    <h1 class="sx-sr-only">Symbiose — Le vivant nous relie</h1>
    <section
      :key="chapter.id"
      class="sx-pitch-scene"
      :class="{
        'sx-pitch-scene--demo': chapter.id === 'meadow',
        'sx-pitch-scene--final': chapter.id === 'night-forest',
      }"
      :aria-label="chapter.subject"
    >
      <p class="sx-eyebrow">
        {{ chapter.subject.toLocaleUpperCase("fr") }}
        <span
          >{{ clock(chapter.start) }}—{{
            clock(chapter.start + chapter.duration)
          }}</span
        >
      </p>
      <img
        v-if="chapter.id === 'night-forest'"
        class="sx-final-logo"
        src="/experience-art/shared/symbiose-logo.png"
        alt="Symbiose"
        width="3634"
        height="1242"
      />
      <h2>{{ chapter.title }}</h2>
      <p class="sx-pitch-message">{{ chapter.message }}</p>
      <p class="sx-evidence-status" :data-status="chapter.status">
        {{ statusLabels[chapter.status] }}
      </p>
      <DemoVideo
        v-if="chapter.id === 'meadow'"
        :suspended="suspended"
        @playing="$emit('videoPlaying')"
      />
      <PitchVisual v-else :chapter="chapter.id" @sources="$emit('sources')" />
      <ul
        v-if="['sky', 'coast', 'night-forest'].includes(chapter.id)"
        class="sx-pitch-points"
      >
        <li v-for="item in chapter.screen" :key="item">{{ item }}</li>
      </ul>
      <p v-if="chapter.id === 'night-forest'" class="sx-next-steps">
        Besoins proposés à confirmer par l’équipe · aucun partenariat annoncé.
      </p>
      <a v-if="chapter.id === 'night-forest'" class="sx-cta" :href="appHref"
        >Commencer l’expérience Symbiose <span aria-hidden="true">↗</span></a
      >
      <button
        v-if="chapter.id === 'forest'"
        class="sx-discover"
        @click="$emit('begin')"
      >
        Découvrir la solution <span aria-hidden="true">↘</span>
      </button>
      <button class="sx-pitch-source" @click="$emit('sources')">
        Sources et texte oral <span aria-hidden="true">↗</span>
      </button>
    </section>
  </div>
</template>
