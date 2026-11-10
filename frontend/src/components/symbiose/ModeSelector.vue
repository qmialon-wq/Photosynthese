<script setup lang="ts">
import { useId } from "vue";
import { useDataMode } from "../../data/data-mode";
import type { DataMode } from "../../data/contracts";
const store = useDataMode();
const id = useId();
defineProps<{ visibleLabel?: boolean }>();
</script>
<template>
  <div class="sym-mode-selector" :class="{ 'sym-mode-selector-labeled': visibleLabel }">
    <label :for="id" :class="{ 'sym-sr-only': !visibleLabel }">{{ visibleLabel ? 'Source de données' : 'Mode de données' }}</label>
    <select
      :id="id"
      :value="store.mode.value"
      @change="
        store.setMode(($event.target as HTMLSelectElement).value as DataMode)
      "
    >
      <option value="demo">Mode démonstration</option>
      <option value="real">Données réelles</option>
    </select>
  </div>
</template>
