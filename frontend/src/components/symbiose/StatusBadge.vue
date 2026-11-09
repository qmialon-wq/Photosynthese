<script setup lang="ts">
import type { VideoStatus } from "../../data/contracts";
import SymIcon from "./SymIcon.vue";
withDefaults(
  defineProps<{
    status: VideoStatus;
    label?: string;
    placement?: "inline" | "overlay";
  }>(),
  { placement: "overlay" },
);
const labels = {
  validated: "Validée",
  pending: "En validation",
  unanalysed: "À analyser",
  unknown: "Non renseigné",
  ready: "Prête",
  processing: "En cours",
  no_detections: "Aucune détection",
  error: "En erreur",
};
const icons = {
  validated: "check",
  pending: "hourglass",
  unanalysed: "refresh",
  unknown: "info",
  ready: "video",
  processing: "hourglass",
  no_detections: "info",
  error: "info",
};
</script>
<template>
  <span
    class="sym-status"
    :class="{
      'sv-status': placement === 'overlay',
      'is-pending': status === 'pending' || status === 'processing',
      'is-unanalysed': !['pending', 'processing', 'validated'].includes(status),
    }"
    ><SymIcon :name="icons[status]" :size="15" />{{
      label || labels[status]
    }}</span
  >
</template>
