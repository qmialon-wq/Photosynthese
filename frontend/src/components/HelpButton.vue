<script setup lang="ts">
import { openClientGuide } from "../client-guide";
import SymIcon from "./symbiose/SymIcon.vue";
</script>
<template>
  <button
    type="button"
    class="sym-circle-button client-help-button"
    aria-label="Aide — guide du compte client"
    title="Aide — découvrir Symbiose"
    aria-haspopup="dialog"
    aria-controls="client-guide"
    @click="openClientGuide"
  >
    <SymIcon name="help" :size="25" />
  </button>
</template>
