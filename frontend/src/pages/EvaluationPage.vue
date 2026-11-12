<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiUrl, date, message, percent, post, useResource } from "../api";
import type { Dataset, Metrics, Model, Operation, Task } from "../types";
const route = useRoute();
const models = useResource<Model[]>(() => "/console/models", 8000),
  datasets = useResource<Dataset[]>(() => "/review/datasets", 10000);
const selected = ref(String(route.query.model || "")),
  datasetId = ref(""),
  split = ref("val"),
  confirmFinalTest = ref(false),
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
watch(
  () => route.query.model,
  (value) => {
    selected.value = String(value || "");
  },
);
async function evaluate() {
  busy.value = true;
  error.value = "";
  evaluation.value = null;
  try {
    taskId.value = (
      await post<Operation>(`/console/models/${selected.value}/evaluate`, {
        dataset_id: datasetId.value,
        split: split.value,
        confirm_final_test: confirmFinalTest.value,
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
interface Benchmark {
  id: string;
  created_at: string;
  dataset_version: string;
  human_validated: boolean;
  protocol: { split: string };
  models: {
    model: { model_id: string; classifier_family: string };
    metrics: Metrics;
    coverage: number;
    failure_rate: number;
    mean_inference_ms: number | null;
    error: string | null;
  }[];
}
const benchmarks = useResource<Benchmark[]>(
  () => "/classification/comparisons",
  10000,
);
function modelName(id: string) {
  return models.data.value?.find((m) => m.id === id)?.name ?? id;
}
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
    <h2>Benchmarks</h2>
    <p class="muted">
      Comparaison des modèles sur les mêmes recadrages de validation. Les scores
      sur labels provisoires sont exploratoires. La sélection du modèle reste
      libre dans la page Modèles.
    </p>
    <LoadState
      :loading="benchmarks.loading.value && !benchmarks.data.value"
      :error="benchmarks.error.value"
      :empty="benchmarks.data.value?.length === 0"
      empty-text="Aucun benchmark terminé"
      @retry="benchmarks.refresh"
    >
      <article
        v-for="benchmark in benchmarks.data.value"
        :key="benchmark.id"
        class="panel"
      >
        <div class="section-head">
          <h3>Benchmark du {{ date(benchmark.created_at) }}</h3>
          <PTag
            :severity="benchmark.human_validated ? 'success' : 'warn'"
            :value="
              benchmark.human_validated
                ? 'Labels humains'
                : 'Labels provisoires'
            "
          />
        </div>
        <p class="muted">
          Dataset {{ benchmark.dataset_version.slice(0, 12) }} ·
          {{ benchmark.protocol.split }}
        </p>
        <div class="table-scroll">
          <table>
            <caption>
              Résultats du benchmark
              {{
                benchmark.id.slice(0, 8)
              }}
            </caption>
            <thead>
              <tr>
                <th>Modèle</th>
                <th>Macro-F1</th>
                <th>Accuracy</th>
                <th>Couverture</th>
                <th>Latence / crop</th>
                <th>Échecs</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in benchmark.models" :key="row.model.model_id">
                <td>
                  <RouterLink
                    :to="{
                      path: '/admin/evaluation',
                      query: { model: row.model.model_id },
                    }"
                  >
                    {{ modelName(row.model.model_id) }}</RouterLink
                  >
                  <p v-if="row.error" role="alert" class="notice error">
                    {{ row.error }}
                  </p>
                </td>
                <td>{{ percent(row.metrics.macro_f1) }}</td>
                <td>{{ percent(row.metrics.accuracy) }}</td>
                <td>{{ percent(row.coverage) }}</td>
                <td>
                  {{
                    row.mean_inference_ms == null
                      ? "Indisponible"
                      : `${row.mean_inference_ms.toFixed(1)} ms`
                  }}
                </td>
                <td>{{ percent(row.failure_rate) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <a
          :href="apiUrl(`/classification/comparisons/${benchmark.id}`)"
          download="benchmark.json"
          >Rapport JSON complet</a
        >
      </article>
    </LoadState>
  </section>
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
      ><label v-if="split === 'test'">
        <input type="checkbox" v-model="confirmFinalTest" required />
        Je confirme l’évaluation finale du modèle sélectionné </label
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
