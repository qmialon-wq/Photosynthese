<script setup lang="ts">
import {
  pendingAdminAction,
  closeAdminConfirmation,
} from "../../admin/confirmation";
import DemoDialog from "../symbiose/DemoDialog.vue";
</script>
<template>
  <DemoDialog
    class="adm-confirmation"
    :open="!!pendingAdminAction"
    :title="pendingAdminAction?.title || 'Confirmation'"
    notice="DONNÉES RÉELLES · AUTORISATION"
    @close="closeAdminConfirmation"
  >
    <template v-if="pendingAdminAction">
      <p>{{ pendingAdminAction.description }}</p>
      <div class="adm-confirm-actions">
        <button class="sv-button-quiet" @click="closeAdminConfirmation">
          Annuler</button
        ><button
          class="sym-button"
          :class="{ 'sym-button-danger': pendingAdminAction.destructive }"
          @click="pendingAdminAction.finish(true)"
        >
          Confirmer l’action réelle
        </button>
      </div>
    </template>
  </DemoDialog>
</template>
