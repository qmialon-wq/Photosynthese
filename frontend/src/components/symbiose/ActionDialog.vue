<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import SymIcon from "./SymIcon.vue";
const props = withDefaults(
  defineProps<{ open: boolean; title: string; notice?: string }>(),
  { notice: "SYMBIOSE NORMANDIE" },
);
const emit = defineEmits<{ close: [] }>();
const dialog = ref<HTMLDialogElement>();
watch(
  () => props.open,
  async (open) => {
    await nextTick();
    if (open && !dialog.value?.open) dialog.value?.showModal();
    else if (!open && dialog.value?.open) dialog.value.close();
  },
  { immediate: true },
);
</script>
<template>
  <dialog
    ref="dialog"
    class="sv-demo-dialog"
    :aria-label="title"
    @close="emit('close')"
  >
    <button
      class="sv-dialog-close"
      aria-label="Fermer la fenêtre"
      @click="dialog?.close()"
    >
      <SymIcon name="close" :size="22" />
    </button>
    <div class="sv-dialog-body">
      <span class="sv-demo-kicker">{{ notice }}</span>
      <h2>{{ title }}</h2>
      <slot />
    </div>
  </dialog>
</template>
