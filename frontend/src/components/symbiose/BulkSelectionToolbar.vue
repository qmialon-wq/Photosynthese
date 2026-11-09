<script setup lang="ts">
import GlassPanel from "./GlassPanel.vue";
import FilterSelect from "./FilterSelect.vue";
import SymIcon from "./SymIcon.vue";
import { observationAssignmentOptions } from "../../data/observation-preview";
const species = defineModel<string>("species", { required: true });
withDefaults(
  defineProps<{
    count: number;
    allSelected: boolean;
    partlySelected: boolean;
    selectable: number;
    enabled?: boolean;
  }>(),
  { enabled: true },
);
const emit = defineEmits<{
  togglePage: [];
  validate: [];
  remove: [];
  clear: [];
}>();
</script>
<template>
  <GlassPanel
    class="sr-bulk-toolbar"
    aria-label="Actions groupées sur les observations"
  >
    <label class="sr-select-page"
      ><input
        type="checkbox"
        :checked="allSelected"
        :indeterminate="partlySelected"
        :disabled="!selectable"
        @change="emit('togglePage')"
      />Sélectionner la page</label
    >
    <span class="sr-selection-count" role="status"
      >{{ count }} sélectionnée{{ count > 1 ? "s" : "" }}</span
    >
    <div class="sr-assign">
      <span aria-hidden="true">Espèce à attribuer</span
      ><FilterSelect
        :disabled="!enabled"
        v-model="species"
        label="Espèce à attribuer"
        :options="observationAssignmentOptions"
      />
    </div>
    <button
      class="sym-button sr-validate"
      :disabled="!enabled || !count || !species"
      :title="
        !count
          ? 'Sélectionnez au moins une observation.'
          : !species
            ? 'Choisissez une espèce à attribuer.'
            : undefined
      "
      @click="emit('validate')"
    >
      <SymIcon name="check" :size="21" />Valider la sélection
    </button>
    <button
      class="sv-button-quiet sr-remove"
      :disabled="!enabled || !count"
      @click="emit('remove')"
    >
      <SymIcon name="trash" :size="19" />Effacer la sélection
    </button>
    <button class="sr-clear" :disabled="!count" @click="emit('clear')">
      Désélectionner
    </button>
  </GlassPanel>
</template>
