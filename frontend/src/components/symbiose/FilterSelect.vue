<script setup lang="ts">
import { useId } from "vue";
import SymIcon from "./SymIcon.vue";
const model = defineModel<string>({ default: "" });
defineProps<{
  label: string;
  options: { value: string; label: string }[];
  disabled?: boolean;
}>();
const id = useId();
</script>
<template>
  <div class="sv-select">
    <label :for="id" class="sym-sr-only">{{ label }}</label
    ><select :id="id" v-model="model" :disabled="disabled">
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option></select
    ><SymIcon name="chevron" :size="17" />
  </div>
</template>
