<script setup lang="ts">
import { useId } from "vue";
import SymIcon from "./SymIcon.vue";
const model = defineModel<string>({ default: "" });
withDefaults(defineProps<{ label?: string; placeholder?: string }>(), {
  label: "Rechercher une vidéo",
  placeholder: "Rechercher une vidéo…",
});
const id = useId();
</script>
<template>
  <div class="sv-search">
    <label :for="id" class="sym-sr-only">{{ label }}</label
    ><SymIcon name="search" :size="20" /><input
      :id="id"
      v-model="model"
      type="search"
      :placeholder="placeholder"
      autocomplete="off"
    />
  </div>
</template>
