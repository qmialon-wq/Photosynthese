<script setup lang="ts">
import { useId } from "vue";
import { useDataMode } from "../../data/data-mode";
import type { DataMode } from "../../data/contracts";
const store = useDataMode();
const id = useId();
</script>
<template>
  <div class="sym-mode-selector">
    <label :for="id" class="sym-sr-only">Mode de données</label>
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
