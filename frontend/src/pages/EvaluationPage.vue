<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { message, post, useResource } from "../api";
import type { Dataset, Metrics, Model, Operation, Task } from "../types";
const route = useRoute();
const models = useResource<Model[]>(() => "/console/models", 8000),
  datasets = useResource<Dataset[]>(() => "/review/datasets", 10000);
const selected = ref(String(route.query.model || "")),
  datasetId = ref(""),
  split = ref("test"),
  taskId = ref(""),
  evaluation = ref<Metrics | null>(null),
  busy = ref(false),
  error = ref("");
const model = computed(() =>
  models.data.value?.find((item) => item.id === selected.value),
);
const metric = computed(
  () =>
    evaluation.value ?? model.value?.metrics.validation ?? model.value?.metrics,
);
watch(selected, () => {
  evaluation.value = null;
  taskId.value = "";
});
async function evaluate() {
  busy.value = true;
  error.value = "";
  evaluation.value = null;
  try {
    taskId.value = (
      await post<Operation>(`/console/models/${selected.value}/evaluate`, {
        dataset_id: datasetId.value,
        split: split.value,
      })
    ).id;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function completed(task: Task) {
  evaluation.value = task.result?.metrics ?? null;
}
const evaluations = useResource<Task[]>(
  () => "/console/tasks?kind=evaluation",
  6000,
);
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">MESURER AVANT DE CONCLURE</p>
      <h1>Évaluation</h1>
      <p class="subtitle">
        Des métriques enregistrées, avec leur jeu de données et leur périmètre.
      </p>
    </div>
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <section class="panel">
    <form class="inline-form" @submit.prevent="evaluate">
      <label
        >Modèle enregistré<select v-model="selected" required>
          <option value="" disabled>Choisir un modèle</option>
          <option
            v-for="item in models.data.value"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }}
          </option>
        </select></label
      ><label
        >Dataset à évaluer<select v-model="datasetId" required>
          <option value="" disabled>Choisir une version</option>
          <option
            v-for="item in datasets.data.value?.filter((d) => d.archive_sha256)"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }}
          </option>
        </select></label
      ><label
        >Split<select v-model="split">
          <option value="test">Test</option>
          <option value="val">Validation</option>
        </select></label
      ><PButton
        type="submit"
        label="Lancer l’évaluation"
        icon="pi pi-chart-bar"
        :loading="busy"
      />
    </form>
    <p class="muted">
      Une évaluation consomme la file du worker et utilise seulement les
      recadrages humainement validés du split choisi.
    </p>
    <p
      v-if="models.error.value || datasets.error.value"
      role="alert"
      class="notice error"
    >
      {{ models.error.value || datasets.error.value }}
    </p>
  </section>
  <TaskPanel v-if="taskId" :key="taskId" :id="taskId" @completed="completed" />
  <MetricsPanel
    v-if="
      metric &&
      (metric.accuracy != null || metric.macro_f1 != null || metric.images)
    "
    :metrics="metric"
    :title="
      evaluation
        ? 'Résultat de l’évaluation'
        : 'Mesures enregistrées avec le checkpoint'
    "
  />
  <div v-else class="panel empty">
    <i class="pi pi-chart-bar" />
    <h2>
      {{
        selected
          ? "Aucune mesure enregistrée pour ce modèle"
          : "Sélectionnez un modèle enregistré"
      }}
    </h2>
    <p>Aucune statistique ne sera estimée pour compléter cet écran.</p>
  </div>
  <section class="panel">
    <h2>Évaluations précédentes</h2>
    <LoadState
      :error="evaluations.error.value"
      :empty="evaluations.data.value?.length === 0"
      empty-text="Aucune évaluation lancée depuis la console"
      @retry="evaluations.refresh"
      ><ul class="plain-list">
        <li v-for="item in evaluations.data.value" :key="item.id">
          <button
            class="text-button"
            @click="
              taskId = item.id;
              evaluation = null;
            "
          >
            Évaluation {{ item.id.slice(0, 8) }}</button
          ><StatusBadge :status="item.status" />
        </li></ul
    ></LoadState>
  </section>
</template>
