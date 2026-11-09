<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { containedMedia, playbackTime } from "../../data/media";
import type { AnalysisVideo } from "../../data/contracts";
import SymIcon from "./SymIcon.vue";
import DetectionOverlay from "./DetectionOverlay.vue";
const props = withDefaults(
  defineProps<{ video: AnalysisVideo; showDetections?: boolean }>(),
  { showDetections: true },
);
const root = ref<HTMLDivElement>(),
  media = ref<HTMLVideoElement>();
const playing = ref(false),
  elapsed = ref(0),
  duration = ref(props.video.duration),
  volume = ref(1),
  volumeOpen = ref(false),
  fullscreen = ref(false),
  error = ref("");
const frame = ref({ width: 3, height: 2 });
const dimensions = ref({
  width: props.video.width,
  height: props.video.height,
});
const viewport = computed(() =>
  containedMedia(
    frame.value.width,
    frame.value.height,
    dimensions.value.width || 3,
    dimensions.value.height || 2,
  ),
);
const surfaceStyle = computed(() => ({
  left: `${viewport.value.x * 100}%`,
  top: `${viewport.value.y * 100}%`,
  width: `${viewport.value.width * 100}%`,
  height: `${viewport.value.height * 100}%`,
}));
const id = useId();
let clock: ReturnType<typeof setInterval> | undefined,
  observer: ResizeObserver | undefined;
function stopClock() {
  if (clock) clearInterval(clock);
  clock = undefined;
}
function startClock() {
  stopClock();
  clock = setInterval(() => {
    elapsed.value = Math.min(duration.value || 0, elapsed.value + 0.1);
    if (elapsed.value >= (duration.value || 0)) {
      playing.value = false;
      stopClock();
    }
  }, 100);
}
async function togglePlayback() {
  if (props.video.kind !== "video" && props.video.playback === "read-only")
    return;
  error.value = "";
  if (props.video.kind === "video") {
    if (!media.value) return;
    try {
      if (media.value.paused) await media.value.play();
      else media.value.pause();
    } catch {
      error.value =
        "La lecture de cette vidéo locale n’est pas disponible dans ce navigateur.";
    }
  } else {
    if (playing.value) {
      playing.value = false;
      stopClock();
    } else {
      if (elapsed.value >= (duration.value || 0)) elapsed.value = 0;
      playing.value = true;
      startClock();
    }
  }
}
function seek(event: Event) {
  const value = Number((event.target as HTMLInputElement).value);
  elapsed.value = Math.max(
    0,
    Math.min(duration.value || 0, Number.isFinite(value) ? value : 0),
  );
  if (media.value && props.video.kind === "video")
    media.value.currentTime = elapsed.value;
}
function metadata() {
  if (!media.value) return;
  if (Number.isFinite(media.value.duration))
    duration.value = media.value.duration;
  dimensions.value = {
    width: media.value.videoWidth || props.video.width,
    height: media.value.videoHeight || props.video.height,
  };
  media.value.volume = volume.value;
}
function changeFullscreen() {
  fullscreen.value = document.fullscreenElement === root.value;
}
async function toggleFullscreen() {
  try {
    if (fullscreen.value) await document.exitFullscreen();
    else await root.value?.requestFullscreen();
  } catch {
    error.value = "Le plein écran n’est pas disponible dans ce navigateur.";
  }
}
watch(volume, (value) => {
  if (media.value) media.value.volume = value;
});
watch(
  () => props.video.id,
  () => {
    media.value?.pause();
    stopClock();
    playing.value = false;
    elapsed.value = 0;
    duration.value = props.video.duration;
    dimensions.value = { width: props.video.width, height: props.video.height };
    error.value = "";
    volumeOpen.value = false;
  },
);
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    if (entry)
      frame.value = {
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      };
  });
  if (root.value) observer.observe(root.value);
  document.addEventListener("fullscreenchange", changeFullscreen);
});
onBeforeUnmount(() => {
  stopClock();
  media.value?.pause();
  observer?.disconnect();
  document.removeEventListener("fullscreenchange", changeFullscreen);
});
</script>
<template>
  <div
    ref="root"
    class="sa-player"
    role="group"
    :aria-label="
      video.accessibleLabel ||
      (video.kind === 'video'
        ? 'Lecteur vidéo local, détection simulée'
        : 'Aperçu fixe, contrôles de lecture simulés')
    "
    @keydown.esc.stop="volumeOpen = false"
  >
    <div class="sa-media-surface" :style="surfaceStyle">
      <video
        v-if="video.kind === 'video'"
        ref="media"
        :src="video.source"
        preload="metadata"
        playsinline
        @loadedmetadata="metadata"
        @timeupdate="elapsed = media?.currentTime || 0"
        @play="playing = true"
        @pause="playing = false"
        @ended="playing = false"
        @error="
          error = 'Cette vidéo locale ne peut pas être lue dans ce navigateur.'
        "
      >
        <track kind="captions" />
      </video>
      <div
        v-else
        class="sa-poster"
        :style="{
          backgroundImage: video.poster ? `url(${video.poster})` : 'none',
          backgroundSize: video.posterSize || 'cover',
          backgroundPosition: video.posterPosition || 'center',
        }"
        role="img"
        :aria-label="
          video.accessibleLabel ||
          `Aperçu de démonstration : ${video.species} en forêt`
        "
      />
      <DetectionOverlay v-if="showDetections" :detections="video.detections" />
    </div>
    <span class="sa-player-demo">{{
      video.notice ||
      (video.kind === "video"
        ? "VIDÉO LOCALE · DÉTECTION SIMULÉE"
        : "IMAGE FIXE · LECTURE SIMULÉE")
    }}</span>
    <div class="sa-player-controls">
      <button
        class="sa-player-button"
        :disabled="video.kind !== 'video' && video.playback === 'read-only'"
        :aria-label="
          video.kind === 'video'
            ? playing
              ? 'Mettre la vidéo locale en pause'
              : 'Lire la vidéo locale'
            : playing
              ? 'Mettre la lecture simulée en pause'
              : 'Démarrer la lecture simulée'
        "
        @click="togglePlayback"
      >
        <SymIcon
          :name="playing ? 'pause' : 'play'"
          :size="24"
          class="sa-play-symbol"
        />
      </button>
      <span class="sa-player-time"
        >{{ playbackTime(elapsed) }} / {{ playbackTime(duration) }}</span
      >
      <label class="sym-sr-only" :for="`${id}-seek`">Position de lecture</label
      ><input
        :id="`${id}-seek`"
        class="sa-seek"
        type="range"
        min="0"
        :max="duration || 0"
        :disabled="video.kind !== 'video' && video.playback === 'read-only'"
        step="0.1"
        :value="elapsed"
        :style="{
          '--sa-progress': `${duration ? (elapsed / duration) * 100 : 0}%`,
        }"
        @input="seek"
      />
      <div class="sa-volume">
        <button
          class="sa-player-button"
          aria-label="Régler le volume"
          :aria-expanded="volumeOpen"
          @click="volumeOpen = !volumeOpen"
        >
          <SymIcon :name="volume === 0 ? 'volume-off' : 'volume'" :size="24" />
        </button>
        <div v-if="volumeOpen" class="sa-volume-popup">
          <label :for="`${id}-volume`">Volume</label
          ><input
            :id="`${id}-volume`"
            v-model.number="volume"
            type="range"
            min="0"
            max="1"
            step="0.05"
          /><button
            class="sa-player-button"
            :aria-label="volume === 0 ? 'Rétablir le son' : 'Couper le son'"
            @click="volume = volume === 0 ? 1 : 0"
          >
            <SymIcon
              :name="volume === 0 ? 'volume-off' : 'volume'"
              :size="20"
            />
          </button>
        </div>
      </div>
      <button
        class="sa-player-button"
        :aria-label="
          fullscreen ? 'Quitter le plein écran' : 'Passer en plein écran'
        "
        @click="toggleFullscreen"
      >
        <SymIcon name="fullscreen" :size="24" />
      </button>
    </div>
    <p v-if="error" class="sa-player-error" role="alert">{{ error }}</p>
  </div>
</template>
