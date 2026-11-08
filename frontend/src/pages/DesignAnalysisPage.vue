<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import VideoPlayer from "../components/symbiose/VideoPlayer.vue";
import AnalysisSettings from "../components/symbiose/AnalysisSettings.vue";
import {
  analysisVideos,
  simulationSteps,
  simulationStepDuration,
} from "../data/analysis-preview";
import "../styles/videotheque.css";
import "../styles/analyse.css";
const selectedId = ref(analysisVideos[0].id),
  objective = ref("species"),
  detail = ref("fast");
const selected = computed(
  () =>
    analysisVideos.find((video) => video.id === selectedId.value) ||
    analysisVideos[0],
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
  <GlassPanel class="sv-page sa-page" topography aria-labelledby="sa-title"
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
        :disabled="phase === 'running'"
        @click="dialog = 'choose'"
      >
        <SymIcon name="plus" :size="27" />Choisir une vidéo
      </button>
    </header>
    <div class="sa-panels">
      <GlassPanel class="sa-video-panel" aria-labelledby="sa-filename"
        ><h2
          id="sa-filename"
          class="sa-panel-heading"
          :title="selected.filename"
        >
          <SymIcon name="file" :size="28" /><span>{{ selected.filename }}</span>
        </h2>
        <VideoPlayer
          :video="selected"
          :show-detections="phase !== 'running'"
        /><GlassPanel class="sa-species-info"
          ><SymIcon name="info" :size="25" />
          <p>
            Espèce suggérée : {{ selected.species }}. Confirmation humaine
            requise.
          </p></GlassPanel
        ></GlassPanel
      ><AnalysisSettings
        v-model:objective="objective"
        v-model:detail="detail"
        :phase="phase"
        :progress="progress"
        @run="run"
        @prepare="dialog = 'crops'"
      />
    </div>
    <DemoDialog
      :open="!!dialog"
      :title="
        dialog === 'choose'
          ? 'Choisir une vidéo'
          : 'Préparer les recadrages à valider'
      "
      @close="dialog = null"
      ><template v-if="dialog === 'choose'"
        ><p>
          Deux aperçus fixes illustrent les contrôles simulés. Une vidéo locale
          d’écureuil peut être réellement lue. Toutes les détections et analyses
          restent fictives.
        </p>
        <div class="sa-video-options">
          <button
            v-for="video in analysisVideos"
            :key="video.id"
            :aria-label="`Sélectionner ${video.filename}`"
            :aria-pressed="selectedId === video.id"
            @click="selectVideo(video.id)"
          >
            <span
              class="sa-option-poster"
              :style="{
                backgroundImage: `url(${video.poster})`,
                backgroundSize: video.posterSize || 'cover',
                backgroundPosition: video.posterPosition || 'center',
              }"
            /><span
              ><strong>{{ video.filename }}</strong
              ><small>{{
                video.kind === "video"
                  ? "Vidéo locale réelle · écureuil · 6,8 s"
                  : "Image fixe · lecture simulée"
              }}</small></span
            ><SymIcon name="check" v-if="selectedId === video.id" :size="20" />
          </button></div></template
      ><template v-else
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
