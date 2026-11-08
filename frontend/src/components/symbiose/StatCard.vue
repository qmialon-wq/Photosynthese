<script setup lang="ts">
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
defineProps<{ icon: string; value: string; label: string; detail: string }>();
</script>
<template>
  <GlassPanel as="article" class="sym-stat"
    ><span class="sym-stat-icon"><SymIcon :name="icon" :size="33" /></span>
    <div>
      <strong>{{ value }}</strong>
      <p>
        {{ label }}<span>{{ detail }}</span>
      </p>
    </div></GlassPanel
  >
</template>
