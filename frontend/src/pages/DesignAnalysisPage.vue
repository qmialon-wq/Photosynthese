<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import VideoPlayer from "../components/symbiose/VideoPlayer.vue";
import AnalysisSettings from "../components/symbiose/AnalysisSettings.vue";
import {
  simulationSteps,
  simulationStepDuration,
} from "../data/analysis-preview";
import "../styles/videotheque.css";
import "../styles/analyse.css";
import { useCollection } from "../data/data-mode";
import { resource, type Detection, type Resource } from "../data/contracts";
import SourceState from "../components/symbiose/SourceState.vue";
const {
  items: analysisVideos,
  state: source,
  store,
} = useCollection("analyses");
const route = useRoute();
const selectedId = ref(analysisVideos.value[0]?.id || ""),
  objective = ref("species"),
  detail = ref("fast");
const selected = computed(
  () =>
    analysisVideos.value.find((video) => video.id === selectedId.value) ||
    analysisVideos.value[0],
);
const report = ref<Resource<Detection>>(resource([]));
watch(
  [analysisVideos, () => route.query.task, () => route.query.video],
  ([list, task, video]) => {
    const requested = list.find((item) =>
      task ? item.id === task : video && item.videoId === video,
    );
    if (requested) {
      selectedId.value = requested.id;
      return;
    }
    if (!list.some((video) => video.id === selectedId.value))
      selectedId.value = list[0]?.id || "";
  },
  { immediate: true },
);
watch(
  () => selected.value?.id,
  async (id) => {
    report.value = resource([]);
    if (
      !id ||
      !store.capabilities.value.readOnly ||
      selected.value?.state !== "completed"
    )
      return;
    report.value = resource([], "loading");
    const result = await store.report(id);
    if (result && selected.value?.id === id) report.value = result;
  },
  { immediate: true },
);
const dialog = ref<"choose" | "crops" | null>(null);
const phase = ref<"idle" | "running" | "completed">("idle"),
  progress = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;
function stopSimulation() {
  if (timer) clearInterval(timer);
  timer = undefined;
}
function reset() {
  stopSimulation();
  phase.value = "idle";
  progress.value = 0;
}
function selectVideo(id: string) {
  selectedId.value = id;
  reset();
  dialog.value = null;
}
function run() {
  if (!store.capabilities.value.simulate) return;
  if (phase.value === "running") return;
  stopSimulation();
  phase.value = "running";
  progress.value = 0;
  let step = 0;
  timer = setInterval(() => {
    progress.value = simulationSteps[step++];
    if (progress.value >= 100) {
      stopSimulation();
      phase.value = "completed";
    }
  }, simulationStepDuration);
}
watch([objective, detail], reset);
onBeforeUnmount(stopSimulation);
</script>
<template>
  <GlassPanel
    depth="page"
    class="sv-page sa-page"
    topography
    aria-labelledby="sa-title"
    ><header class="sv-header sa-header">
      <div class="sv-heading">
        <span class="sv-heading-icon"
          ><SymIcon name="sparkles" :size="41"
        /></span>
        <div>
          <h1 id="sa-title">Analyse vidéo</h1>
          <p>Suivez chaque traitement et retrouvez ses résultats localisés.</p>
        </div>
      </div>
      <button
        class="sym-button sv-import sa-choose"
        :disabled="phase === 'running' || !analysisVideos.length"
        @click="dialog = 'choose'"
      >
        <SymIcon name="plus" :size="27" />Choisir une vidéo
      </button>
    </header>
    <SourceState
      :resource="source"
      empty-text="Aucune analyse enregistrée."
      @retry="store.refresh"
    />
    <div class="sa-panels">
      <GlassPanel
        v-if="selected"
        class="sa-video-panel"
        aria-labelledby="sa-filename"
        ><h2
          id="sa-filename"
          class="sa-panel-heading"
          :title="selected.filename"
        >
          <SymIcon name="file" :size="28" /><span>{{
            selected.filename || `Analyse ${selected.id}`
          }}</span>
        </h2>
        <VideoPlayer
          :video="selected"
          :show-detections="phase !== 'running'"
        /><GlassPanel class="sa-species-info"
          ><SymIcon name="info" :size="25" />
          <p>
            Espèce suggérée : {{ selected.species || "Non disponible" }}.
            Confirmation humaine requise.
          </p></GlassPanel
        ></GlassPanel
      ><AnalysisSettings
        :enabled="store.capabilities.value.simulate"
        :caption="
          store.capabilities.value.readOnly
            ? 'Modèle utilisé : consulter le rapport enregistré. Aucun moteur n’est lancé depuis cet écran.'
            : undefined
        "
        v-model:objective="objective"
        v-model:detail="detail"
        :phase="phase"
        :progress="progress"
        @run="run"
        @prepare="dialog = 'crops'"
      />
    </div>
    <GlassPanel
      v-if="
        store.capabilities.value.readOnly && selected?.state === 'completed'
      "
      class="sa-video-panel"
    >
      <h2>Détections enregistrées</h2>
      <SourceState
        :resource="report"
        empty-text="Aucune détection dans ce rapport."
      />
      <ul v-if="report.data.length" class="sym-report-list">
        <li v-for="detection in report.data" :key="detection.id">
          {{ detection.time ?? "—" }} s · {{ detection.label }} ·
          {{
            detection.confidence == null
              ? "Confiance non disponible"
              : `${(detection.confidence * 100).toFixed(1)} %`
          }}
        </li>
      </ul>
    </GlassPanel>
    <RouterLink
      v-if="store.isReal.value && selected?.videoId"
      class="sym-button"
      :to="{
        path: `/videos/${encodeURIComponent(selected.videoId)}/dossier`,
        query: { analysis: selected.id },
      }"
      >Lire le dossier et les recommandations de cette vidéo</RouterLink
    >
    <DemoDialog
      :notice="
        store.capabilities.value.readOnly
          ? 'DONNÉES RÉELLES · CONSULTATION'
          : undefined
      "
      :open="!!dialog"
      :title="
        dialog === 'choose'
          ? 'Choisir une vidéo'
          : 'Préparer les recadrages à valider'
      "
      @close="dialog = null"
      ><template v-if="dialog === 'choose'"
        ><p>
          {{
            store.capabilities.value.readOnly
              ? "Choisissez une analyse enregistrée. Les traitements en cours et les erreurs conservent leur état réel."
              : "Deux aperçus fixes illustrent les contrôles simulés. Une vidéo locale d’écureuil peut être réellement lue. Toutes les détections et analyses restent fictives."
          }}
        </p>
        <div class="sa-video-options">
          <button
            v-for="video in analysisVideos"
            :key="video.id"
            :aria-label="`Sélectionner ${video.filename || video.id}`"
            :aria-pressed="selectedId === video.id"
            @click="selectVideo(video.id)"
          >
            <span
              class="sa-option-poster"
              :style="{
                backgroundImage: video.poster ? `url(${video.poster})` : 'none',
                backgroundSize: video.posterSize || 'cover',
                backgroundPosition: video.posterPosition || 'center',
              }"
            /><span
              ><strong>{{ video.filename || `Analyse ${video.id}` }}</strong
              ><small>{{
                store.capabilities.value.readOnly
                  ? video.state || "État non disponible"
                  : video.kind === "video"
                    ? "Vidéo locale réelle · écureuil · 6,8 s"
                    : "Image fixe · lecture simulée"
              }}</small></span
            ><SymIcon name="check" v-if="selectedId === video.id" :size="20" />
          </button></div></template
      ><template v-else-if="selected"
        ><p>Préparation simulée pour {{ selected.filename }}.</p>
        <p>
          Aucun recadrage n’est extrait ni enregistré. Cette étape illustre une
          action distincte de l’analyse et prépare la future validation humaine.
        </p>
        <button class="sym-button" @click="dialog = null">
          J’ai compris
        </button></template
      ></DemoDialog
    >
  </GlassPanel>
</template>
