<script setup lang="ts">
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
import FilterSelect from "./FilterSelect.vue";
import AnalysisStatus from "./AnalysisStatus.vue";
import {
  analysisObjectives,
  analysisDetailOptions,
  detailCaptions,
  modelCaption,
} from "../../data/analysis-preview";
const objective = defineModel<string>("objective", { required: true });
const detail = defineModel<string>("detail", { required: true });
withDefaults(
  defineProps<{
    phase: "idle" | "running" | "completed";
    progress: number;
    enabled?: boolean;
    caption?: string;
  }>(),
  { enabled: true, caption: modelCaption },
);
const emit = defineEmits<{ run: []; prepare: [] }>();
</script>
<template>
  <GlassPanel class="sa-settings" aria-labelledby="sa-settings-title"
    ><h2 id="sa-settings-title" class="sa-panel-heading">
      <SymIcon name="sliders" :size="29" />Configurer l’analyse
    </h2>
    <GlassPanel class="sa-setting-block"
      ><fieldset :disabled="!enabled || phase === 'running'">
        <legend class="sym-sr-only">Objectif de l’analyse</legend>
        <h3>Objectif de l’analyse</h3>
        <FilterSelect
          v-model="objective"
          label="Objectif de l’analyse"
          :options="analysisObjectives"
        />
        <p>{{ caption }}</p>
      </fieldset></GlassPanel
    >
    <GlassPanel class="sa-setting-block"
      ><fieldset :disabled="!enabled || phase === 'running'">
        <legend class="sym-sr-only">Niveau de détail</legend>
        <h3>Niveau de détail</h3>
        <FilterSelect
          v-model="detail"
          label="Niveau de détail"
          :options="analysisDetailOptions"
        />
        <p>
          {{
            enabled
              ? detailCaptions[detail]
              : "Paramètres non appliqués en consultation."
          }}
        </p>
      </fieldset></GlassPanel
    >
    <button
      class="sym-button sa-run"
      :disabled="!enabled || phase === 'running'"
      :aria-busy="phase === 'running'"
      @click="emit('run')"
    >
      <SymIcon
        :name="phase === 'running' ? 'hourglass' : 'play'"
        :size="24"
      />{{ phase === "running" ? "Analyse en cours…" : "Lancer l’analyse" }}
    </button>
    <AnalysisStatus v-if="enabled" :phase="phase" :progress="progress" />
    <p v-else class="sym-read-only">
      Lancement et préparation indisponibles dans cet écran en lecture seule.
    </p>
    <button
      class="sa-prepare-crops"
      :disabled="!enabled || phase === 'running'"
      @click="emit('prepare')"
    >
      <SymIcon name="layers" :size="24" />Préparer les recadrages à valider
    </button>
    <div class="sa-settings-info">
      <SymIcon name="info" :size="24" />
      <p>
        La classification utilise le modèle actif au lancement.<br />La
        préparation des recadrages est une tâche distincte.
      </p>
    </div>
  </GlassPanel>
</template>
