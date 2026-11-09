<script setup lang="ts">
import {
  corpusSpeciesLabel,
  retrievalLabels,
  type DemoRetrievalTask,
} from "../../data/document-preview";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
import DocumentEmptyState from "./DocumentEmptyState.vue";
withDefaults(
  defineProps<{ task: DemoRetrievalTask | null; emptyMessage?: string }>(),
  { emptyMessage: "Aucune récupération en cours." },
);
</script>
<template>
  <GlassPanel
    class="sd-progress-panel"
    topography
    aria-labelledby="sd-progress-title"
    ><h2 id="sd-progress-title" class="sd-section-title">
      <SymIcon name="chart" :size="30" />Avancement
    </h2>
    <DocumentEmptyState v-if="!task" compact :message="emptyMessage" />
    <div v-else class="sd-task">
      <div class="sd-task-heading">
        <strong
          >Récupération simulée · {{ task.species.length }} espèce{{
            task.species.length > 1 ? "s" : ""
          }}</strong
        ><span class="sd-task-status" role="status">{{
          retrievalLabels[task.status]
        }}</span>
      </div>
      <p>{{ task.species.map(corpusSpeciesLabel).join(" · ") }}</p>
      <div class="sd-task-progress">
        <progress
          max="100"
          :value="task.progress"
          aria-label="Progression de la récupération simulée"
        /><span>{{ task.progress }} %</span>
      </div>
      <p class="sd-task-note">
        {{
          task.status === "completed"
            ? "Exemples fictifs ajoutés au corpus. Aucun article recherché ou téléchargé."
            : "Démonstration locale · aucune recherche ni aucun téléchargement réel."
        }}
      </p>
    </div></GlassPanel
  >
</template>
