<script setup lang="ts">
import { computed, ref, watch } from "vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import FilterSelect from "../components/symbiose/FilterSelect.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import ObservationCard from "../components/symbiose/ObservationCard.vue";
import BulkSelectionToolbar from "../components/symbiose/BulkSelectionToolbar.vue";
import ValidationPreviewModal from "../components/symbiose/ValidationPreviewModal.vue";
import {
  editableSelection,
  filterDemoObservations,
  observationQualityFilters,
  observationSpeciesLabel,
  removeDemoObservations,
  validateDemoObservations,
  type DemoObservation,
} from "../data/observation-preview";
import "../styles/videotheque.css";
import "../styles/validation.css";

import { useCollection } from "../data/data-mode";
import SourceState from "../components/symbiose/SourceState.vue";
const {
  items: observations,
  state: source,
  store,
} = useCollection("observations");
const observationSpeciesFilters = computed(() => [
  { value: "", label: "Toutes les espèces" },
  ...store.data.species.data,
]);
const speciesFilter = ref(""),
  qualityFilter = ref(""),
  assignedSpecies = ref("");
const selected = ref(new Set<string>()),
  feedback = ref("");
const confirmation = ref<"validate" | "remove" | null>(null),
  preview = ref<DemoObservation | null>(null);
const visible = computed(() =>
  filterDemoObservations(
    observations.value,
    speciesFilter.value,
    qualityFilter.value,
  ),
);
const selectable = computed(() =>
  visible.value.filter((observation) => !observation.protected),
);
const selection = computed(() =>
  editableSelection(visible.value, selected.value),
);
const allSelected = computed(
  () =>
    !!selectable.value.length &&
    selection.value.length === selectable.value.length,
);
const partlySelected = computed(
  () => !!selection.value.length && !allSelected.value,
);
function clearSelection() {
  selected.value.clear();
}
watch([speciesFilter, qualityFilter], () => {
  clearSelection();
  feedback.value = "";
  confirmation.value = null;
});
function toggle(id: string) {
  if (!selectable.value.some((observation) => observation.id === id)) return;
  if (selected.value.has(id)) selected.value.delete(id);
  else selected.value.add(id);
}
function togglePage() {
  if (allSelected.value) clearSelection();
  else
    selected.value = new Set(
      selectable.value.map((observation) => observation.id),
    );
}
function requestConfirmation(action: "validate" | "remove") {
  if (!store.capabilities.value.simulate) return;
  if (
    !selection.value.length ||
    (action === "validate" && !assignedSpecies.value)
  )
    return;
  confirmation.value = action;
}
function confirm() {
  if (!store.capabilities.value.simulate) return;
  const ids = new Set(selection.value.map((observation) => observation.id));
  if (!ids.size) {
    confirmation.value = null;
    return;
  }
  if (confirmation.value === "validate") {
    if (!assignedSpecies.value) return;
    observations.value = validateDemoObservations(
      observations.value,
      ids,
      assignedSpecies.value,
    );
    feedback.value = `Démonstration : ${ids.size} observation${ids.size > 1 ? "s" : ""} validée${ids.size > 1 ? "s" : ""} comme « ${observationSpeciesLabel(assignedSpecies.value)} ». Aucun enregistrement serveur.`;
  } else if (confirmation.value === "remove") {
    observations.value = removeDemoObservations(observations.value, ids);
    feedback.value = `Démonstration : ${ids.size} observation${ids.size > 1 ? "s" : ""} retirée${ids.size > 1 ? "s" : ""} de la liste locale. Aucun fichier réel n’a été supprimé.`;
  }
  clearSelection();
  confirmation.value = null;
}
function resetFilters() {
  speciesFilter.value = "";
  qualityFilter.value = "";
}
</script>
<template>
  <GlassPanel
    depth="page"
    class="sv-page sr-page"
    topography
    aria-labelledby="sr-title"
  >
    <header class="sv-header sr-header">
      <div class="sv-heading">
        <span class="sv-heading-icon"
          ><SymIcon name="check-square" :size="41"
        /></span>
        <div>
          <h1 id="sr-title">Validation humaine</h1>
          <p>Vérifiez chaque observation pour confirmer l’espèce détectée.</p>
        </div>
      </div>
      <div class="sr-filters">
        <FilterSelect
          v-model="speciesFilter"
          label="Filtrer les observations par espèce"
          :options="observationSpeciesFilters"
        /><FilterSelect
          v-model="qualityFilter"
          label="Filtrer les observations par qualité"
          :options="observationQualityFilters"
        />
      </div>
    </header>
    <SourceState
      :resource="source"
      empty-text="Aucune observation disponible."
      @retry="store.refresh"
    />
    <p v-if="store.capabilities.value.readOnly" class="sym-read-only">
      Validation et retrait désactivés : consultation en lecture seule.
    </p>
    <BulkSelectionToolbar
      :enabled="store.capabilities.value.simulate"
      v-model:species="assignedSpecies"
      :count="selection.length"
      :all-selected="allSelected"
      :partly-selected="partlySelected"
      :selectable="selectable.length"
      @toggle-page="togglePage"
      @validate="requestConfirmation('validate')"
      @remove="requestConfirmation('remove')"
      @clear="clearSelection"
    />
    <div class="sr-information">
      <SymIcon name="info" :size="21" />
      <p>
        Vérifiez chaque animal avant d’attribuer une espèce. Les noms de
        fichiers sont des suggestions. La sélection est limitée à cette page :
        les images de test générées restent protégées.
      </p>
    </div>
    <p v-if="feedback" class="sr-feedback" role="status">{{ feedback }}</p>
    <div
      v-if="visible.length"
      class="sr-observation-grid"
      aria-label="Observations de démonstration"
    >
      <ObservationCard
        v-for="observation in visible"
        :key="observation.id"
        :observation="observation"
        :selected="selected.has(observation.id)"
        @toggle="toggle"
        @preview="preview = $event"
      />
    </div>
    <div v-else-if="source.state === 'success'" class="sr-empty">
      <SymIcon name="search" :size="30" />
      <h2>Aucune observation à afficher</h2>
      <p>
        {{
          observations.length
            ? "Essayez une autre espèce ou une autre qualité."
            : "Toutes les observations ont été retirées de cette démonstration."
        }}
      </p>
      <button
        v-if="speciesFilter || qualityFilter"
        class="sv-button-quiet"
        @click="resetFilters"
      >
        Réinitialiser les filtres
      </button>
    </div>
    <DemoDialog
      :open="!!confirmation"
      :title="
        confirmation === 'validate'
          ? 'Valider la sélection'
          : 'Effacer la sélection'
      "
      @close="confirmation = null"
      ><template v-if="confirmation"
        ><p v-if="confirmation === 'validate'">
          Confirmer la validation fictive de
          {{ selection.length }} observation{{
            selection.length > 1 ? "s" : ""
          }}
          comme « {{ observationSpeciesLabel(assignedSpecies) }} » ? Cette
          action reste locale et ne réalise aucune classification.
        </p>
        <p v-else>
          Retirer {{ selection.length }} observation{{
            selection.length > 1 ? "s" : ""
          }}
          de la liste de démonstration ? Aucun fichier réel ne sera supprimé.
          Les images de test protégées sont conservées.
        </p>
        <div class="sr-dialog-actions">
          <button class="sv-button-quiet" @click="confirmation = null">
            Annuler</button
          ><button class="sym-button" @click="confirm">
            {{
              confirmation === "validate"
                ? "Confirmer la validation"
                : "Confirmer le retrait simulé"
            }}
          </button>
        </div></template
      ></DemoDialog
    >
    <ValidationPreviewModal
      :read-only="store.capabilities.value.readOnly"
      :observation="preview"
      @close="preview = null"
    />
  </GlassPanel>
</template>
