<script setup lang="ts">
import type { Observation } from "../../data/contracts";
import DemoDialog from "./DemoDialog.vue";
import VideoPlayer from "./VideoPlayer.vue";
import "../../styles/analyse.css";
defineProps<{ observation: Observation | null; readOnly?: boolean }>();
const emit = defineEmits<{ close: [] }>();
</script>
<template>
  <DemoDialog
    class="sr-preview-modal"
    :notice="readOnly ? 'DONNÉES ENREGISTRÉES · CONSULTATION' : undefined"
    :open="!!observation"
    :title="
      observation
        ? `Observation ${observation.number} · ${observation.filename}`
        : 'Aperçu de l’observation'
    "
    @close="emit('close')"
  >
    <template v-if="observation"
      ><p class="sr-preview-description">
        {{
          readOnly
            ? "Observation enregistrée. Aucune validation ni génération d’extrait n’est effectuée."
            : observation.media.kind === "video"
              ? "Lecture du fichier local d’écureuil. Les informations de validation sont fictives."
              : "Aperçu statique de démonstration. Les contrôles de lecture sont simulés."
        }}
      </p>
      <VideoPlayer
        :key="observation.id"
        :video="observation.media"
        :show-detections="false"
      />
      <p class="sr-preview-context">
        {{ observation.context }}
        {{
          readOnly ? "" : "· contexte de démonstration, aucun extrait généré."
        }}
      </p>
      <p v-if="observation.protected" class="sr-preview-protection">
        Image de test protégée : cette observation ne peut être ni validée ni
        retirée.
      </p></template
    >
  </DemoDialog>
</template>
