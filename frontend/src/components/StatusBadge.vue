<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ status: string }>();
const labels: Record<string, string> = {
  queued: "En attente",
  running: "En cours",
  completed: "Terminé",
  error: "Erreur",
  cancelled: "Annulé",
  pending: "À revoir",
  validated: "Validé",
  corrected: "Corrigé",
  rejected: "Rejeté",
  ready: "Disponible",
  processing: "Préparation",
  no_detections: "Aucune détection",
  interrupted: "Interrompu",
};
const severity = computed(() =>
  ["error", "rejected"].includes(props.status)
    ? "danger"
    : ["completed", "ready", "validated", "corrected"].includes(props.status)
      ? "success"
      : ["running", "processing"].includes(props.status)
        ? "info"
        : "secondary",
);
</script>
<template>
  <PTag :value="labels[status] || status" :severity="severity" />
</template>
