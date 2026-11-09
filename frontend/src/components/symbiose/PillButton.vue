<script setup lang="ts">
import SymIcon from "./SymIcon.vue";
defineProps<{ to: string }>();
</script>
<template>
  <RouterLink :to="to" class="sym-button"
    ><slot /><SymIcon name="arrow" :size="22"
  /></RouterLink>
</template>
