<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { RouterLink } from "vue-router";
import NarrativeOverlay from "../experience/NarrativeOverlay.vue";
import PresentationControls from "../experience/PresentationControls.vue";
import { NarrativeTimeline } from "../experience/NarrativeTimeline";
import { scrollScreens } from "../experience/config";
import {
  appUrl,
  chapterProgress,
  pitchChapters,
  pitchIndex,
  pitchSeconds,
  progressAtSeconds,
} from "../experience/pitch";
import type { PerformanceSample } from "../experience/PerformanceMonitor";
import "../experience/experience.css";
import "../experience/journey.css";
import "../experience/pitch.css";
import "../experience/finishing.css";
import symbioseLogo from "../assets/symbiose-logo.png";
import FallbackScene from "../experience/FallbackScene.vue";
import JourneyAnnotations from "../experience/JourneyAnnotations.vue";
import FaunaAnnotations from "../experience/FaunaAnnotations.vue";
import {
  defaultLayers,
  transitions,
  transitionProgress,
  referenceScene,
  type JourneyLayers,
} from "../experience/journey";
import type { FrameReport } from "../experience/telemetry";
import {
  ownsPresentationKey,
  readCheckpoint,
  saveCheckpoint,
  type JuryCheckpoint,
} from "../experience/jury-state";
const props = withDefaults(
  defineProps<{ jury?: boolean; applicationHref?: string }>(),
  { jury: false, applicationHref: appUrl },
);
const ExperienceCanvas = defineAsyncComponent(
  () => import("../experience/ExperienceCanvas.vue"),
);
const DebugControls = defineAsyncComponent(
  () => import("../experience/DebugControls.vue"),
);
const checkpoint = ref<JuryCheckpoint>();
const restartGeneration = ref(0);
const forced2d = ref(
  new URLSearchParams(location.search).get("render") === "2d",
);

const root = ref<HTMLElement>();
const progress = ref(0),
  ready = ref(false),
  error = ref("");
const mode = ref<"exploration" | "presentation">(
  props.jury ? "presentation" : "exploration",
);
const playing = ref(false),
  systemReduced = ref(false),
  userReduced = ref(false);
const reducedMotion = computed(() => systemReduced.value || userReduced.value);
const dialog = ref<HTMLDialogElement>();
const dialogOpen = ref(false),
  fullscreen = ref(false),
  fullscreenNote = ref("");
const PitchSources = defineAsyncComponent(
  () => import("../experience/PitchSources.vue"),
);
let fullscreenOwned = false;
const performance = ref<PerformanceSample>();
const frame = ref<FrameReport>();
const layers = ref<JourneyLayers>({ ...defaultLayers });
const assetIssues = ref<string[]>([]);
function showFallback(message: string) {
  error.value = message;
  frame.value = undefined;
}
const debug = ["experience", "transitions"].includes(
  new URLSearchParams(window.location.search).get("debug") ?? "",
);
const reference = computed(() => referenceScene(progress.value));
function setLayer(key: keyof JourneyLayers, value: boolean) {
  layers.value = { ...layers.value, [key]: value };
}
let timeline: NarrativeTimeline | undefined;
let media: MediaQueryList;
let resizeObserver: ResizeObserver;
let resizeFrame = 0;
const originalTitle = document.title;
const originalScrollRestoration = history.scrollRestoration;
function buildTimeline() {
  timeline?.dispose();
  if (root.value)
    timeline = new NarrativeTimeline(
      root.value,
      reducedMotion.value,
      (value) => (progress.value = value),
      () => (playing.value = false),
    );
}
function mediaChanged() {
  systemReduced.value = media.matches;
  buildTimeline();
}
function toggleMotion() {
  userReduced.value = !userReduced.value;
  buildTimeline();
}
function seek(value: number, immediate = props.jury) {
  timeline?.seek(value, immediate);
}
function restart() {
  timeline?.pause();
  restartGeneration.value++;
  checkpoint.value = undefined;
  seek(0, true);
  if (props.jury) saveCheckpoint(0, mode.value);
  root.value?.focus({ preventScroll: true });
}
function skipAnimation() {
  const index = pitchIndex(progress.value);
  seek(index === 7 ? 1 : chapterProgress(index + 1), true);
}
function resume() {
  if (checkpoint.value) {
    mode.value = checkpoint.value.mode;
    seek(checkpoint.value.progress, true);
    root.value?.focus({ preventScroll: true });
  }
}
function toggleRenderer() {
  timeline?.pause();
  forced2d.value = !(forced2d.value || !!error.value);
  if (!forced2d.value) {
    error.value = "";
    ready.value = false;
  }
  frame.value = undefined;
}
function persist() {
  if (props.jury) saveCheckpoint(progress.value, mode.value);
}
watch(
  () => pitchIndex(progress.value),
  () => persist(),
);
function setMode(value: "exploration" | "presentation") {
  timeline?.pause();
  mode.value = value;
}
function play() {
  if (!reducedMotion.value) {
    if (progress.value >= 0.999) {
      seek(0);
    }
    timeline?.playPresentation();
    playing.value = true;
  }
}
function openProject() {
  timeline?.pause();
  dialogOpen.value = true;
  dialog.value?.showModal();
}
function fullscreenChanged() {
  fullscreen.value = !!document.fullscreenElement;
}
async function toggleFullscreen() {
  timeline?.pause();
  fullscreenNote.value = "";
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
      fullscreenOwned = true;
    } else
      fullscreenNote.value =
        "Le plein écran n’est pas disponible dans ce navigateur.";
  } catch {
    fullscreenNote.value =
      "Le navigateur a refusé le plein écran. Les contrôles restent disponibles.";
  }
}
function presentationKey(event: KeyboardEvent) {
  if (
    mode.value !== "presentation" ||
    dialogOpen.value ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey
  )
    return;
  if (!ownsPresentationKey(event)) return;
  const index = pitchIndex(progress.value);
  if (["ArrowRight", "ArrowDown", "PageDown"].includes(event.key)) {
    event.preventDefault();
    seek(index === 7 ? 1 : chapterProgress(index + 1));
  } else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) {
    event.preventDefault();
    seek(chapterProgress(index - 1));
  } else if (event.key === "Home" || event.key === "End") {
    event.preventDefault();
    seek(event.key === "Home" ? 0 : 1);
  } else if (event.key === " ") {
    event.preventDefault();
    playing.value ? timeline?.pause() : play();
  }
}

onMounted(() => {
  document.title = "Symbiose — Le vivant nous relie";
  media = window.matchMedia("(prefers-reduced-motion: reduce)");
  systemReduced.value = media.matches;
  media.addEventListener("change", mediaChanged);
  if (props.jury) {
    checkpoint.value = readCheckpoint();
    history.scrollRestoration = "manual";
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  buildTimeline();
  window.addEventListener("pagehide", persist);
  window.addEventListener("keydown", presentationKey);
  document.addEventListener("fullscreenchange", fullscreenChanged);
  const query = new URLSearchParams(location.search),
    id = transitions.find((t) => t.id === query.get("transition"))?.id;
  if (debug && id) seek(transitionProgress(id, Number(query.get("p") ?? 0)));
  resizeObserver = new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => timeline?.refresh());
  });
  resizeObserver.observe(root.value!);
});
onBeforeUnmount(() => {
  timeline?.dispose();
  resizeObserver?.disconnect();
  cancelAnimationFrame(resizeFrame);
  media?.removeEventListener("change", mediaChanged);
  window.removeEventListener("keydown", presentationKey);
  window.removeEventListener("pagehide", persist);
  document.removeEventListener("fullscreenchange", fullscreenChanged);
  if (fullscreenOwned && document.fullscreenElement)
    void document.exitFullscreen().catch(() => {});
  dialog.value?.close();
  document.title = originalTitle;
  if (props.jury) history.scrollRestoration = originalScrollRestoration;
});
</script>

<template>
  <main
    ref="root"
    id="main-content"
    tabindex="-1"
    class="landing sx-experience"
    :data-mode="mode"
    :data-reduced-motion="reducedMotion"
    :data-progress="progress.toFixed(6)"
    :data-jury="jury"
    :style="{
      '--sx-scroll-screens': scrollScreens,
      '--sx-flow': `${-progress * 96}px`,
    }"
  >
    <div
      class="sx-stage"
      :class="{
        'sx-stage--ready': ready,
        'sx-stage--fallback': error || forced2d,
      }"
    >
      <ExperienceCanvas
        v-if="!error && !forced2d"
        :progress="progress"
        :reduced-motion="reducedMotion"
        :layers="layers"
        :suspended="dialogOpen"
        @ready="ready = true"
        @error="showFallback"
        @performance="performance = $event"
        @frame="frame = $event"
        @assets="assetIssues = $event"
      />
      <FallbackScene
        v-else
        :progress="progress"
        :reduced-motion="reducedMotion"
        @ready="ready = true"
      />
      <div class="sx-vignette" aria-hidden="true" />
      <header class="sx-header">
        <component
          :is="jury ? 'a' : RouterLink"
          class="sx-brand"
          v-bind="jury ? { href: '/jury/' } : { to: '/' }"
          aria-label="Symbiose Normandie — accueil"
        >
          <img :src="symbioseLogo" alt="Symbiose" width="3634" height="1242" />
        </component>
        <span class="sx-event"
          >UN PROJET NORMAND<span>Datathon Normandie · 2026</span></span
        >
        <nav aria-label="Navigation d’accueil">
          <button class="sx-project-link" @click="openProject">
            Le projet <span aria-hidden="true">+</span></button
          ><a class="sx-app-link" :href="applicationHref"
            >Accéder à l’application <span aria-hidden="true">↗</span></a
          >
        </nav>
      </header>
      <NarrativeOverlay
        v-if="!debug"
        :key="restartGeneration"
        :progress="progress"
        :reduced-motion="reducedMotion"
        :suspended="dialogOpen"
        :app-href="applicationHref"
        @begin="seek(chapterProgress(1))"
        @sources="openProject"
      />
      <h1 v-else class="sx-sr-only">Symbiose — Le vivant nous relie</h1>
      <JourneyAnnotations
        v-if="debug"
        :frame="frame"
        :visible="layers.observation"
      />
      <FaunaAnnotations v-if="frame?.animals?.length" :animals="frame.animals" />
      <div class="sx-location">
        <span class="sx-location-mark" aria-hidden="true">⌖</span> NORMANDIE,
        FRANCE<span class="sx-location-rule" aria-hidden="true" /><span>{{
          "TRAJET ILLUSTRATIF · NON GÉOLOCALISÉ"
        }}</span>
      </div>
      <div class="sx-prototype">
        <span>VOYAGE · 8 ATMOSPHÈRES</span
        ><button @click="openProject">
          {{
            error || forced2d
              ? "Version simplifiée 2D · images générées"
              : "Reconstruction 3D · calques générés"
          }}
          <span aria-hidden="true">↗</span>
        </button>
      </div>
      <p
        v-if="assetIssues.length && !debug"
        class="sx-motion-note"
        role="status"
      >
        Certains calques sont indisponibles · géométrie conservée
      </p>
      <p v-if="!ready && !error" class="sx-loading" role="status">
        Préparation du paysage…
      </p>
      <div v-if="error" class="sx-fallback-note" role="status">
        <p>{{ error }}</p>
        <button @click="openProject">Lire le projet et le parcours</button>
      </div>
      <p v-if="reducedMotion" class="sx-motion-note">
        Mouvements réduits · points de vue fixes
      </p>
      <PresentationControls
        :progress="progress"
        :mode="mode"
        :playing="playing"
        :reduced-motion="reducedMotion"
        :fullscreen="fullscreen"
        :fallback="!!error || forced2d"
        :resume-label="
          checkpoint
            ? pitchChapters[pitchIndex(checkpoint.progress)].subject
            : undefined
        "
        @seek="seek"
        @mode="setMode"
        @play="play"
        @pause="timeline?.pause()"
        @fullscreen="toggleFullscreen"
        @restart="restart"
        @skip="skipAnimation"
        @resume="resume"
        @renderer="toggleRenderer"
      />
      <p v-if="fullscreenNote" class="sx-fullscreen-note" role="status">
        {{ fullscreenNote }}
      </p>
      <DebugControls
        v-if="debug"
        :progress="progress"
        :layers="layers"
        :frame="frame"
        :performance="performance"
        :issues="assetIssues"
        :fallback="!!error"
        @seek="seek"
        @layer="setLayer"
      />
      <figure v-if="debug && layers.reference" class="sx-debug-reference">
        <img
          :src="`/experience-art/${reference}/primary-v1.png`"
          alt="Composition de référence générée par IA"
        />
        <figcaption>
          Référence fixe · {{ reference }} · image générée
        </figcaption>
      </figure>
    </div>
    <dialog
      ref="dialog"
      class="sx-dialog"
      aria-labelledby="sx-project-title"
      @close="dialogOpen = false"
      @click="$event.target === dialog && dialog?.close()"
    >
      <div class="sx-dialog-inner">
        <button
          class="sx-dialog-close"
          autofocus
          aria-label="Fermer le projet"
          @click="dialog?.close()"
        >
          Fermer <span aria-hidden="true">×</span>
        </button>
        <PitchSources
          v-if="dialogOpen"
          :chapter-id="pitchChapters[pitchIndex(progress)].id"
        />
        <p class="sx-resource-note">
          Ce voyage relie huit milieux par une reconstruction 3D d’intention et
          des calques générés. Les tracés, signaux et animaux sont illustratifs
          ; aucun score d’IA ni relevé cadastral n’est calculé ici. Étretat est
          une évocation, et les changements de lieu ne sont pas une captation
          réelle. Les fonds reconstruits et profondeurs calibrées de production
          restent absents. Les informations du pitch sont distinctes de ces
          illustrations ; les archives IGN sont datées et consultables
          localement.
        </p>
        <div class="sx-dialog-actions">
          <a v-if="!jury" href="/experience-art/index.html"
            >Voir les huit atmosphères ↗</a
          >
          <RouterLink v-if="!jury" class="sx-cta" to="/inscription"
            >Créer un compte <span aria-hidden="true">↗</span></RouterLink
          ><a :href="applicationHref">Se connecter</a
          ><button
            v-if="!systemReduced"
            :aria-pressed="userReduced"
            @click="toggleMotion"
          >
            {{
              userReduced ? "Activer les mouvements" : "Réduire les mouvements"
            }}</button
          ><span v-else>Mouvements réduits par le système</span>
        </div>
      </div>
    </dialog>
  </main>
</template>
