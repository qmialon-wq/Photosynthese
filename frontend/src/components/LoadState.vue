<script setup lang="ts">
defineProps<{
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyText?: string;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div v-if="error" class="notice error" role="alert">
    <i class="pi pi-exclamation-circle" aria-hidden="true" /> {{ error }}
    <PButton
      label="Réessayer"
      severity="secondary"
      size="small"
      @click="$emit('retry')"
    />
  </div>
  <p v-else-if="loading" class="loading" role="status">
    <i class="pi pi-spin pi-spinner" aria-hidden="true" /> Chargement des
    données…
  </p>
  <div v-else-if="empty" class="empty">
    <i class="pi pi-inbox" aria-hidden="true" />
    <h3>{{ emptyText || "Aucune donnée pour le moment" }}</h3>
    <slot name="empty" />
  </div>
  <slot v-if="!empty" />
</template>
