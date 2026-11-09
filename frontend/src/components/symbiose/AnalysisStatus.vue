<script setup lang="ts">
defineProps<{ phase: "idle" | "running" | "completed"; progress: number }>();
</script>
<template>
  <div class="sa-analysis-status">
    <div v-if="phase === 'running'" class="sa-analysis-progress" role="status">
      <span>Analyse simulée en cours · {{ progress }} %</span
      ><progress
        max="100"
        :value="progress"
        aria-label="Progression de l’analyse simulée"
      />
    </div>
    <p
      v-else-if="phase === 'completed'"
      class="sa-analysis-completed"
      role="status"
    >
      Analyse terminée — résultat de démonstration
    </p>
    <p class="sa-simulation-note">Démonstration · aucun traitement réel</p>
  </div>
</template>
