<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import ParcelProject from "../components/ParcelProject.vue";
import "../styles/dossier-reader.css";
const route = useRoute();
const videoId = computed(() => String(route.params.id));
const analysisId = computed(() =>
  typeof route.query.analysis === "string" ? route.query.analysis : "",
);
</script>

<template>
  <GlassPanel depth="page" class="dossier-reader" topography>
    <RouterLink to="/analyses">Retour aux analyses</RouterLink>
    <h1>Dossier biodiversité de la vidéo</h1>
    <ParcelProject
      :key="`${videoId}:${analysisId}`"
      :video-id="videoId"
      :analysis-id="analysisId"
      :completed="false"
      read-only
    />
  </GlassPanel>
</template>
