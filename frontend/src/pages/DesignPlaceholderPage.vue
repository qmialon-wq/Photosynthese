<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { symbioseNavigation } from "../symbiose-navigation";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import PillButton from "../components/symbiose/PillButton.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
const route = useRoute();
const item = computed(
  () =>
    symbioseNavigation.find((section) => section.path === route.path) ||
    symbioseNavigation[0],
);
</script>
<template>
  <GlassPanel class="sym-placeholder" topography
    ><span class="sym-placeholder-icon"
      ><SymIcon :name="item.icon" :size="42"
    /></span>
    <p class="sym-eyebrow">SYMBIOSE · APERÇU GRAPHIQUE</p>
    <h1>{{ item.label }}</h1>
    <p>
      La structure est prête. Cette rubrique sera intégrée lors d’une prochaine
      étape.
    </p>
    <PillButton to="/">Revenir à l’Accueil</PillButton></GlassPanel
  >
</template>
