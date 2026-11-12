<script setup lang="ts">
import { computed, ref } from "vue";
import { apiUrl, date, message, post, useResource } from "../api";
import type { Dataset, Operation, Sample } from "../types";
const datasets = useResource<Dataset[]>(() => "/review/datasets", 5000);
const selected = ref(""),
  detail = useResource<Dataset>(() =>
    selected.value ? `/review/datasets/${selected.value}` : null,
  );
const name = ref(""),
  excludeSmall = ref(true),
  excludeBlur = ref(false),
  excludeDuplicate = ref(false),
  excludedGroups = ref(""),
  busy = ref(false),
  error = ref(""),
  operationId = ref("");
const operation = useResource<{
  status: string;
  error?: string;
  result?: { dataset_id: string };
}>(
  () => (operationId.value ? `/review/operations/${operationId.value}` : null),
  2000,
);
const distribution = computed(() => {
  const counts: Record<string, { train: number; val: number; test: number }> =
    {};
  for (const sample of detail.data.value?.manifest?.samples ?? []) {
    const label = sample.label!;
    counts[label] ??= { train: 0, val: 0, test: 0 };
    if (sample.split in counts[label])
      counts[label][sample.split as "train" | "val" | "test"]++;
  }
  return counts;
});
const qualityCount = (flag: "blurry" | "too_small" | "near_duplicate") =>
  (detail.data.value?.manifest?.samples ?? []).filter(
    (sample: Sample) => sample.quality?.[flag] || sample.frame_quality?.[flag],
  ).length;
async function create() {
  busy.value = true;
  error.value = "";
  try {
    const flags = [
      ...(excludeSmall.value ? ["too_small"] : []),
      ...(excludeBlur.value ? ["blurry"] : []),
      ...(excludeDuplicate.value ? ["near_duplicate"] : []),
    ];
    operationId.value = (
      await post<Operation>("/review/datasets", {
        name: name.value,
        exclude_quality: flags,
        exclude_groups: excludedGroups.value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      })
    ).id;
    name.value = "";
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function rebuild() {
  busy.value = true;
  error.value = "";
  try {
    operationId.value = (
      await post<Operation>(`/review/datasets/${selected.value}/rebuild`)
    ).id;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">DONNÉES VALIDÉES · VERSIONS IMMUTABLES</p>
      <h1>Datasets</h1>
      <p class="subtitle">
        Construisez des jeux reproductibles, séparés par groupe vidéo.
      </p>
    </div>
  </div>
  <div class="two-columns">
    <section class="panel">
      <h2>Créer une version</h2>
      <form class="form-grid" @submit.prevent="create">
        <label
          >Nom de la version<input
            v-model="name"
            required
            pattern="[a-zA-Z0-9_-]{1,80}"
            placeholder="normandie-v1"
        /></label>
        <fieldset>
          <legend>Exclusions de qualité</legend>
          <label class="check-line"
            ><input v-model="excludeSmall" type="checkbox" /> Recadrages trop
            petits</label
          ><label class="check-line"
            ><input v-model="excludeBlur" type="checkbox" /> Images
            floues</label
          ><label class="check-line"
            ><input v-model="excludeDuplicate" type="checkbox" />
            Quasi-doublons</label
          >
        </fieldset>
        <label
          >Groupes à exclure, séparés par une virgule<input
            v-model="excludedGroups"
            placeholder="groupe-camera-001, groupe-camera-002"
        /></label>
        <p class="muted">
          Seuls les exemples validés ou corrigés, avec rendu terminé, sont
          exportés. Le test inclus est gelé et les fuites entre splits bloquent
          l’export.
        </p>
        <PButton
          type="submit"
          label="Construire le dataset"
          icon="pi pi-database"
          :loading="busy"
        />
      </form>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <div v-if="operation.data.value" class="notice" role="status">
        <StatusBadge :status="operation.data.value.status" />
        <p v-if="operation.data.value.error">
          {{ operation.data.value.error }}
        </p>
        <PButton
          v-if="operation.data.value.result?.dataset_id"
          label="Consulter la version"
          severity="secondary"
          @click="
            selected = operation.data.value.result!.dataset_id;
            datasets.refresh();
          "
        />
      </div>
    </section>
    <section class="panel">
      <h2>Versions enregistrées</h2>
      <LoadState
        :error="datasets.error.value"
        :loading="datasets.loading.value && !datasets.data.value"
        :empty="datasets.data.value?.length === 0"
        empty-text="Aucune version publiée"
        @retry="datasets.refresh"
        ><ul class="version-list">
          <li v-for="item in datasets.data.value" :key="item.id">
            <button
              :class="{ active: selected === item.id }"
              @click="selected = item.id"
            >
              <span
                ><strong>{{ item.name }}</strong
                ><small>{{ date(item.created_at) }} · {{ item.actor }}</small
                ><code>{{ item.id.slice(0, 16) }}</code></span
              ><StatusBadge
                :status="item.archive_sha256 ? 'ready' : 'processing'"
              />
            </button>
          </li></ul
      ></LoadState>
    </section>
  </div>
  <LoadState
    :error="detail.error.value"
    :loading="detail.loading.value"
    @retry="detail.refresh"
    ><template v-if="detail.data.value?.manifest"
      ><section class="panel">
        <div class="section-head">
          <div>
            <span class="eyebrow"
              >VERSION {{ detail.data.value.id.slice(0, 12) }}</span
            >
            <h2>{{ detail.data.value.name }}</h2>
          </div>
          <div class="actions">
            <a
              v-if="detail.data.value.archive_sha256"
              class="button-link"
              :href="apiUrl(`/review/datasets/${selected}/archive`)"
              download
              ><i class="pi pi-download" /> Télécharger le ZIP</a
            ><PButton
              label="Reconstruire à l’identique"
              severity="secondary"
              :disabled="busy"
              @click="rebuild"
            />
          </div>
        </div>
        <div class="stat-grid compact">
          <div class="stat">
            <span>Exemples validés</span
            ><strong>{{ detail.data.value.manifest.samples.length }}</strong>
          </div>
          <div class="stat">
            <span>Indicateur de flou</span
            ><strong>{{ qualityCount("blurry") }}</strong>
          </div>
          <div class="stat">
            <span>Très petits</span
            ><strong>{{ qualityCount("too_small") }}</strong>
          </div>
          <div class="stat">
            <span>Similaires</span
            ><strong>{{ qualityCount("near_duplicate") }}</strong>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Espèce</th>
                <th>Train</th>
                <th>Validation</th>
                <th>Test</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(counts, label) in distribution" :key="label">
                <th scope="row">{{ label }}</th>
                <td>{{ counts.train }}</td>
                <td>{{ counts.val }}</td>
                <td>{{ counts.test }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted mono">
          SHA-256 archive :
          {{ detail.data.value.archive_sha256 || "Export en cours" }}
        </p>
      </section></template
    ></LoadState
  >
</template>
