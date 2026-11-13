<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { localMediaUrl } from "./pitch";
import { posterUrl } from "./runtime-assets";
const props = defineProps<{ suspended: boolean }>();
const emit = defineEmits<{ playing: [] }>();
const localFiles = Object.keys(
  import.meta.glob("/public/experience-media/demo.{mp4,webm}", {
    eager: true,
    query: "?url",
    import: "default",
  }),
);
const configured = import.meta.env.VITE_SYMBIOSE_DEMO_URL as string | undefined;
const src = ref(
  localMediaUrl(configured) || localFiles[0]?.replace("/public", "") || "",
);
const captions = localMediaUrl(import.meta.env.VITE_SYMBIOSE_DEMO_CAPTIONS_URL);
const video = ref<HTMLVideoElement>();
const failed = ref(false),
  fileName = ref(""),
  notice = ref("");
const playing = ref(false),
  duration = ref(0);
let objectUrl = "";
const available = computed(() => !!src.value && !failed.value);
const durationNote = computed(() => {
  if (!Number.isFinite(duration.value))
    return "Durée non déterminée. Vérifiez que le montage tient dans le créneau de 90 secondes.";
  return duration.value && Math.abs(duration.value - 90) > 5
    ? `Durée du fichier : ${Math.round(duration.value)} s. Le créneau prévu est de 90 s ; adaptez le montage pour le pitch.`
    : "";
});
function pause() {
  video.value?.pause();
  playing.value = false;
}
function fail() {
  pause();
  failed.value = true;
  notice.value =
    "Vidéo absente ou illisible. La capture du manifeste reste disponible.";
}
async function toggle() {
  if (!video.value || props.suspended) return;
  if (!video.value.paused) pause();
  else {
    try {
      await video.value.play();
    } catch {
      if (!failed.value)
        notice.value =
          "Lecture impossible. Essayez les contrôles du lecteur ou un autre fichier local.";
    }
  }
}
function chooseFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (!/^video\//.test(file.type) && !/\.(mp4|webm)$/i.test(file.name)) {
    notice.value = "Choisissez une vidéo MP4 ou WebM.";
    return;
  }
  pause();
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  src.value = objectUrl;
  failed.value = false;
  fileName.value = file.name;
  duration.value = 0;
  notice.value =
    "Fichier ouvert sur cet appareil, sans téléversement. Lancez la lecture manuellement.";
}
function onPlay() {
  if (props.suspended || document.hidden) {
    pause();
    return;
  }
  playing.value = true;
  emit("playing");
}
const visibility = () => {
  if (document.hidden) pause();
};
watch(
  () => props.suspended,
  (value) => {
    if (value) pause();
  },
);
onMounted(() => {
  document.addEventListener("visibilitychange", visibility);
  if (configured && !localMediaUrl(configured))
    notice.value =
      "La vidéo doit utiliser un chemin local. Configuration distante ignorée.";
});
onBeforeUnmount(() => {
  pause();
  document.removeEventListener("visibilitychange", visibility);
  if (objectUrl) URL.revokeObjectURL(objectUrl);
});
defineExpose({ pause });
</script>
<template>
  <figure class="sx-demo" aria-labelledby="sx-demo-title">
    <div class="sx-demo-bar">
      <span id="sx-demo-title">SYMBIOSE / VALIDATION HUMAINE</span
      ><span>02:30–04:00 · DÉMO</span>
    </div>
    <div class="sx-demo-screen">
      <video
        v-if="available"
        ref="video"
        :key="src"
        :src="src"
        controls
        playsinline
        preload="none"
        muted
        :poster="posterUrl"
        aria-label="Démonstration vidéo de l’application Symbiose"
        @error="fail"
        @play="onPlay"
        @pause="playing = false"
        @ended="playing = false"
        @loadedmetadata="duration = video?.duration ?? 0"
      >
        <track
          v-if="captions"
          kind="captions"
          label="Français"
          srclang="fr"
          :src="captions"
          default
        />
        Votre navigateur ne peut pas lire cette vidéo locale.
      </video>
      <template v-else>
        <img
          :src="posterUrl"
          alt="Capture de l’écran de validation humaine Symbiose, extraite du manifeste ARQ, page 7. Données d’illustration, sans preuve de performance."
          width="1907"
          height="895"
        />
        <div class="sx-demo-placeholder">
          <strong>La vraie interface. La vidéo reste à fournir.</strong
          ><span>Capture du manifeste · page 7 · remplacement statique</span>
        </div>
      </template>
    </div>
    <figcaption>
      <span>{{
        fileName ||
        (available
          ? "Vidéo locale configurée · lecture manuelle"
          : "Vidéo produit de 90 s non fournie")
      }}</span>
      <button v-if="available" class="sx-demo-toggle" @click="toggle">
        {{ playing ? "Mettre la vidéo en pause" : "Lancer la vidéo" }}
      </button>
      <label class="sx-file-choice"
        >Choisir une vidéo locale<input
          type="file"
          accept="video/mp4,video/webm,.mp4,.webm"
          aria-label="Choisir une vidéo locale"
          @change="chooseFile"
      /></label>
    </figcaption>
    <p v-if="notice || durationNote" class="sx-media-notice" role="status">
      {{ notice }} {{ durationNote }}
    </p>
    <details class="sx-demo-guide">
      <summary>Parcours à montrer · préparation accessible</summary>
      <p>
        Importer une vidéo, examiner et valider une proposition animale,
        retrouver le projet localisé, puis lire une alternative avec ses sources
        et conditions. Ce fil de démonstration ne remplace pas les sous-titres
        du fichier réel. Ajouter une piste WebVTT locale pour une vidéo
        commentée.
      </p>
    </details>
  </figure>
</template>
