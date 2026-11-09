<script setup lang="ts">
import type { Resource } from "../../data/contracts";
import SymIcon from "./SymIcon.vue";
defineProps<{
  resource: Pick<Resource<unknown>, "state" | "message">;
  emptyText?: string;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div
    v-if="resource.state !== 'success' || resource.message"
    class="sym-source-state"
    :role="resource.state === 'error' ? 'alert' : 'status'"
    :aria-busy="resource.state === 'loading'"
  >
    <SymIcon
      :name="resource.state === 'loading' ? 'refresh' : 'info'"
      :size="22"
    />
    <p>
      {{
        resource.message ||
        (resource.state === "loading"
          ? "Chargement des données…"
          : resource.state === "empty"
            ? emptyText || "Aucune donnée disponible."
            : "Fonctionnalité non connectée.")
      }}
    </p>
    <RouterLink
      v-if="resource.message.includes('Connexion requise')"
      class="sv-button-quiet"
      to="/connexion"
      >Se connecter</RouterLink
    >
    <button
      v-else-if="resource.state === 'error' || resource.state === 'unconnected'"
      class="sv-button-quiet"
      @click="$emit('retry')"
    >
      Réessayer
    </button>
  </div>
</template>
