<script setup lang="ts">
import SymIcon from "./SymIcon.vue";
withDefaults(defineProps<{ message: string; compact?: boolean }>(), {
  compact: false,
});
</script>
<template>
  <div class="sd-empty-state" :class="{ 'is-compact': compact }">
    <span class="sd-empty-icon"><SymIcon name="inbox" :size="33" /></span>
    <p>{{ message }}</p>
  </div>
</template>
