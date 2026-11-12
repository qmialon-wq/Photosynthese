<script setup lang="ts">
import type { ScientificDocument } from "../../data/contracts";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
const corpusSpeciesLabel = (value: string) =>
  value
    ? value[0].toLocaleUpperCase("fr-FR") + value.slice(1).replaceAll("-", " ")
    : "";
withDefaults(
  defineProps<{
    documents: ScientificDocument[];
    selected: ReadonlySet<string>;
    actionLabel?: string;
    selectable?: boolean;
  }>(),
  { actionLabel: "Consulter", selectable: true },
);
const emit = defineEmits<{
  toggle: [id: string];
  preview: [document: ScientificDocument];
}>();
</script>
<template>
  <div class="sd-document-list" aria-label="Documents scientifiques">
    <GlassPanel
      v-for="document in documents"
      :key="document.id"
      as="article"
      class="sd-document-card"
      :class="{ 'is-selected': selected.has(document.id) }"
      :data-document-id="document.id"
      :aria-labelledby="`${document.id}-title`"
      ><input
        v-if="selectable"
        type="checkbox"
        :checked="selected.has(document.id)"
        :aria-label="`Sélectionner ${document.title}`"
        @change="emit('toggle', document.id)"
      /><span class="sd-file-icon"><SymIcon name="file" :size="28" /></span>
      <div class="sd-document-copy">
        <h3 :id="`${document.id}-title`" :title="document.title">
          {{ document.title }}
        </h3>
        <p>
          {{ corpusSpeciesLabel(document.species) || "Espèce non renseignée" }}
          · {{ document.kind || "—" }} · {{ document.date || "—" }}
          {{ document.dateNote }}
        </p>
      </div>
      <button
        class="sv-button-quiet"
        :aria-label="`${actionLabel} ${document.title}`"
        @click="emit('preview', document)"
      >
        {{ actionLabel }}
      </button></GlassPanel
    >
  </div>
</template>
