<script setup lang="ts">
import { computed, watch } from "vue";
import { apiUrl, message, post, taskLabel, useResource } from "../api";
import type { Task } from "../types";
import { ref } from "vue";
const props = defineProps<{ id: string }>();
const emit = defineEmits<{ completed: [task: Task] }>();
const task = useResource<Task>(() => `/console/tasks/${props.id}`, 2000);
const logs = useResource<
  Array<{ id: number; message: string; created_at: string }>
>(() => `/console/tasks/${props.id}/logs`, 3000);
const actionError = ref("");
const cancelling = ref(false);
const progress = computed(() => {
  const p = task.data.value?.progress;
  return p?.total ? Math.min(100, (100 * (p.current ?? 0)) / p.total) : null;
});
watch(
  () => task.data.value?.status,
  (value) => {
    if (value === "completed" && task.data.value)
      emit("completed", task.data.value);
  },
);
async function cancel() {
  cancelling.value = true;
  try {
    await post(`/console/tasks/${props.id}/cancel`);
    await task.refresh();
  } catch (error) {
    actionError.value = message(error);
  } finally {
    cancelling.value = false;
  }
}
</script>
<template>
  <section class="panel task-panel" aria-label="Suivi de tâche">
    <LoadState
      :loading="task.loading.value && !task.data.value"
      :error="task.error.value"
      @retry="task.refresh"
    >
      <template v-if="task.data.value">
        <div class="section-head">
          <div>
            <span class="eyebrow">TRAITEMENT LOCAL</span>
            <h3>
              {{ taskLabel(task.data.value.kind) }}
              <StatusBadge :status="task.data.value.status" />
            </h3>
          </div>
          <PButton
            v-if="['queued', 'running'].includes(task.data.value.status)"
            label="Demander l’arrêt"
            severity="secondary"
            icon="pi pi-stop"
            :loading="cancelling"
            :disabled="task.data.value.cancel_requested"
            @click="cancel"
          />
        </div>
        <p v-if="task.data.value.cancel_requested" role="status">
          Arrêt demandé, en attente d’un point d’interruption sûr.
        </p>
        <p>
          {{
            task.data.value.progress.stage ||
            (task.data.value.status === "queued"
              ? "En attente du worker disponible"
              : "Consulter les journaux ci-dessous")
          }}
        </p>
        <div v-if="progress !== null">
          <PProgressBar :value="Math.round(progress)" /><small
            >{{ task.data.value.progress.current }} /
            {{ task.data.value.progress.total }}</small
          >
        </div>
        <PProgressBar
          v-else-if="task.data.value.status === 'running'"
          mode="indeterminate"
          style="height: 6px"
          aria-label="Traitement en cours, progression non mesurée"
        />
        <p
          v-if="task.data.value.error || actionError"
          class="notice error"
          role="alert"
        >
          {{ actionError || task.data.value.error }}
        </p>
        <div
          v-if="
            task.data.value.kind === 'analysis' &&
            task.data.value.status === 'completed'
          "
          class="actions"
        >
          <a :href="apiUrl(`/console/tasks/${id}/artifacts/video`)" download
            >MP4 annoté <i class="pi pi-download"
          /></a>
          <a :href="apiUrl(`/console/tasks/${id}/artifacts/report`)" download
            >Rapport JSON <i class="pi pi-download"
          /></a>
        </div>
        <details>
          <summary>Journal du traitement</summary>
          <p v-if="logs.error.value" role="alert">{{ logs.error.value }}</p>
          <pre class="logs">{{
            logs.data.value
              ?.map((line) => `${line.created_at}  ${line.message}`)
              .join("\n") || "Aucun événement supplémentaire."
          }}</pre>
        </details>
      </template>
    </LoadState>
  </section>
</template>
