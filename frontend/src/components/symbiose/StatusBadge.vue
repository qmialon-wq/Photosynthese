<script setup lang="ts">
import type { VideoStatus } from "../../data/video-preview";
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
};
const icons = {
  validated: "check",
  pending: "hourglass",
  unanalysed: "refresh",
};
</script>
<template>
  <span
    class="sym-status"
    :class="{
      'sv-status': placement === 'overlay',
      'is-pending': status === 'pending',
      'is-unanalysed': status === 'unanalysed',
    }"
    ><SymIcon :name="icons[status]" :size="15" />{{
      label || labels[status]
    }}</span
  >
</template>
