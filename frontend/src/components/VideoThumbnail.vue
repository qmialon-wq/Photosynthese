<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  source?: string;
  poster?: string;
  label: string;
}>();
const root = ref<HTMLElement>();
const image = ref(props.poster || "");
const active = ref(false);
const failed = ref(false);
let observer: IntersectionObserver | undefined;
let timer: ReturnType<typeof setTimeout> | undefined;
function clearTimer() {
  if (timer) clearTimeout(timer);
}
function unavailable() {
  clearTimer();
  failed.value = true;
}
function imageError() {
  if (image.value === props.poster && props.source) image.value = "";
  else unavailable();
}
function midpoint(event: Event) {
  const video = event.target as HTMLVideoElement;
  if (!Number.isFinite(video.duration) || video.duration <= 0) {
    unavailable();
    return;
  }
  // Même règle pour toutes les vidéos : une image à 50 % de leur durée.
  video.currentTime = video.duration / 2;
}
function capture(event: Event) {
  const video = event.target as HTMLVideoElement;
  if (!video.videoWidth || !video.videoHeight || video.readyState < 2) return;
  if (
    !Number.isFinite(video.duration) ||
    Math.abs(video.currentTime - video.duration / 2) > 0.05
  )
    return;
  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 480 / video.videoWidth);
  canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
  try {
    const context = canvas.getContext("2d");
    if (!context) return unavailable();
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    image.value = canvas.toDataURL("image/jpeg", 0.8);
    clearTimer();
    // Retirer la source arrête les lectures réseau après extraction de l'image.
    queueMicrotask(() => {
      video.removeAttribute("src");
      video.load();
    });
  } catch {
    unavailable();
  }
}
watch(
  () => [props.source, props.poster],
  () => {
    clearTimer();
    image.value = props.poster || "";
    failed.value = false;
  },
);
watch(
  () => [active.value, props.source, image.value, failed.value],
  () => {
    clearTimer();
    if (active.value && props.source && !image.value && !failed.value)
      timer = setTimeout(unavailable, 20000);
  },
  { immediate: true },
);
onMounted(() => {
  if (typeof IntersectionObserver === "undefined") {
    active.value = true;
    return;
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        active.value = true;
        observer?.disconnect();
      }
    },
    { rootMargin: "150px" },
  );
  if (root.value) observer.observe(root.value);
});
onBeforeUnmount(() => {
  clearTimer();
  observer?.disconnect();
});
</script>

<template>
  <span
    ref="root"
    class="video-midpoint-thumbnail"
    role="img"
    :aria-label="label"
  >
    <img v-if="image && !failed" :src="image" alt="" @error="imageError" />
    <video
      v-else-if="active && source && !failed"
      :key="source"
      :src="source"
      preload="metadata"
      muted
      playsinline
      tabindex="-1"
      aria-hidden="true"
      @loadedmetadata="midpoint"
      @seeked="capture"
      @error="unavailable"
    />
    <span v-else class="video-thumbnail-fallback" aria-hidden="true"
      >Aperçu indisponible</span
    >
  </span>
</template>

<style scoped>
.video-midpoint-thumbnail {
  display: block;
  position: relative;
  overflow: hidden;
  background: #20372e;
}
.video-midpoint-thumbnail img,
.video-midpoint-thumbnail video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.video-midpoint-thumbnail video {
  visibility: hidden;
}
.video-thumbnail-fallback {
  display: grid;
  place-items: center;
  height: 100%;
  padding: 0.5rem;
  font-size: 0.8rem;
  color: #fff;
  text-align: center;
}
</style>
