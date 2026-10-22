<script setup lang="ts">
import { computed } from "vue";
import { percent } from "../api";
import type { Metrics } from "../types";
const props = defineProps<{ metrics: Metrics; title?: string }>();
const metric = computed(
  () => props.metrics.images ?? props.metrics.validation ?? props.metrics,
);
const errors = computed(() => {
  const rows: Array<{ truth: string; predicted: string; count: number }> = [];
  metric.value.confusion_matrix?.forEach((row, i) =>
    row.forEach((count, j) => {
      if (i !== j && count)
        rows.push({
          truth: metric.value.classes?.[i] ?? String(i),
          predicted: metric.value.classes?.[j] ?? String(j),
          count,
        });
    }),
  );
  return rows.sort((a, b) => b.count - a.count).slice(0, 8);
});
</script>
<template>
  <section class="panel metrics-panel">
    <div class="section-head">
      <h2>{{ title || "Métriques de classification" }}</h2>
      <span class="muted">{{ metrics.split || "Validation" }}</span>
    </div>
    <div class="stat-grid compact">
      <div class="stat">
        <span>Accuracy par image</span
        ><strong>{{ percent(metric.accuracy) }}</strong>
      </div>
      <div class="stat">
        <span>Macro-F1 par image</span
        ><strong>{{ percent(metric.macro_f1) }}</strong>
      </div>
      <div class="stat">
        <span>Images évaluées</span
        ><strong>{{ metric.count ?? "Non renseigné" }}</strong>
      </div>
    </div>
    <p v-if="metrics.videos?.accuracy != null">
      Accuracy vidéo : {{ percent(metrics.videos.accuracy) }} · macro-F1 vidéo :
      {{ percent(metrics.videos.macro_f1) }}
    </p>
    <p v-else class="muted">
      Métriques vidéo non disponibles sans vérité terrain vidéo validée.
    </p>
    <template v-if="metric.confusion_matrix?.length && metric.classes">
      <h3>Matrice de confusion</h3>
      <p class="muted">Lignes : espèce réelle · Colonnes : espèce prédite</p>
      <div class="table-scroll">
        <table class="confusion">
          <caption class="sr-only">
            Matrice de confusion de classification
          </caption>
          <thead>
            <tr>
              <th scope="col">Réel / Prédit</th>
              <th v-for="label in metric.classes" :key="label" scope="col">
                {{ label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in metric.confusion_matrix" :key="i">
              <th scope="row">{{ metric.classes[i] }}</th>
              <td
                v-for="(value, j) in row"
                :key="j"
                :class="{
                  diagonal: i === j,
                  'off-diagonal': i !== j && value > 0,
                }"
              >
                {{ value }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <h3>Confusions fréquentes</h3>
      <ul v-if="errors.length" class="plain-list">
        <li v-for="row in errors" :key="`${row.truth}-${row.predicted}`">
          <span>{{ row.truth }} → {{ row.predicted }}</span
          ><strong>{{ row.count }}</strong>
        </li>
      </ul>
      <p v-else>Aucune confusion dans cette évaluation.</p>
    </template>
    <p v-else class="muted">
      Aucune matrice de confusion enregistrée pour cette mesure.
    </p>
  </section>
</template>
