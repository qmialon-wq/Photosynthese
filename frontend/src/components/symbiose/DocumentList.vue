<script setup lang="ts">
import type { DemoScientificDocument } from "../../data/document-preview";
import { corpusSpeciesLabel } from "../../data/document-preview";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
defineProps<{
  documents: DemoScientificDocument[];
  selected: ReadonlySet<string>;
}>();
const emit = defineEmits<{
  toggle: [id: string];
  preview: [document: DemoScientificDocument];
}>();
</script>
<template>
  <div class="sd-document-list" aria-label="Documents de démonstration">
    <GlassPanel
      v-for="document in documents"
      :key="document.id"
      as="article"
      class="sd-document-card"
      :class="{ 'is-selected': selected.has(document.id) }"
      :data-document-id="document.id"
      :aria-labelledby="`${document.id}-title`"
      ><input
        type="checkbox"
        :checked="selected.has(document.id)"
        :aria-label="`Sélectionner ${document.title}`"
        @change="emit('toggle', document.id)"
      /><span class="sd-file-icon"><SymIcon name="file" :size="28" /></span>
      <div class="sd-document-copy">
        <h3 :id="`${document.id}-title`">{{ document.title }}</h3>
        <p>
          {{ corpusSpeciesLabel(document.species) }} · {{ document.kind }} ·
          {{ document.date }} (date fictive)
        </p>
      </div>
      <button
        class="sv-button-quiet"
        :aria-label="`Consulter ${document.title}`"
        @click="emit('preview', document)"
      >
        Consulter
      </button></GlassPanel
    >
  </div>
</template>
