<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { date, message, percent, post, useResource } from "../api";
import type { Dataset, Epoch, Operation, Run, Task } from "../types";
const route = useRoute(),
  router = useRouter();
const datasets = useResource<Dataset[]>(() => "/review/datasets", 10000);
const tasks = useResource<Task[]>(() => "/console/tasks?kind=training", 3000);
const runs = useResource<Run[]>(() => "/training/runs", 4000);
const selected = ref(String(route.query.task || "")),
  busy = ref(false),
  error = ref("");
const metrics = useResource<Epoch[]>(
  () => (selected.value ? `/training/runs/${selected.value}/metrics` : null),
  4000,
);
const config = ref({
  dataset_id: "",
  model_name: "tf_efficientnetv2_b0",
  batch_size: 2,
  accumulation_steps: 4,
  image_size: 224,
  epochs_head: 6,
  epochs_finetune: 18,
  patience: 6,
  amp: "auto",
});
async function launch() {
  busy.value = true;
  error.value = "";
  try {
    selected.value = (
      await post<Operation>("/console/training", config.value)
    ).id;
    await router.replace({ query: { task: selected.value } });
    await tasks.refresh();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function select(id: string) {
  selected.value = id;
  void router.replace({ query: { task: id } });
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">CLASSIFICATION · PYTORCH</p>
      <h1>Entraînements</h1>
      <p class="subtitle">
        Configurez un run local. Une seule tâche GPU lourde s’exécute à la fois.
      </p>
    </div>
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <section class="panel">
    <h2>Nouvel entraînement</h2>
    <form class="form-grid training-form" @submit.prevent="launch">
      <label class="wide"
        >Dataset versionné<select v-model="config.dataset_id" required>
          <option value="" disabled>Choisir un dataset validé</option>
          <option
            v-for="item in datasets.data.value?.filter((d) => d.archive_sha256)"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }} · {{ item.id.slice(0, 8) }}
          </option>
        </select></label
      ><label
        >Backbone<select v-model="config.model_name">
          <option value="tf_efficientnetv2_b0">EfficientNetV2 B0</option>
          <option value="efficientnetv2_s">EfficientNetV2 S</option>
          <option value="convnext_tiny">ConvNeXt Tiny</option>
        </select></label
      ><label
        >Batch<input
          v-model.number="config.batch_size"
          type="number"
          min="1"
          max="64"
          required /></label
      ><label
        >Accumulation de gradients<input
          v-model.number="config.accumulation_steps"
          type="number"
          min="1"
          max="64"
          required /></label
      ><label
        >Taille d’image<input
          v-model.number="config.image_size"
          type="number"
          min="32"
          max="512"
          required /></label
      ><label
        >Époques : tête<input
          v-model.number="config.epochs_head"
          type="number"
          min="1"
          max="200"
          required /></label
      ><label
        >Époques : fine-tuning<input
          v-model.number="config.epochs_finetune"
          type="number"
          min="1"
          max="500"
          required /></label
      ><label
        >Patience early stopping<input
          v-model.number="config.patience"
          type="number"
          min="1"
          max="100"
          required /></label
      ><label
        >Précision mixte<select v-model="config.amp">
          <option value="auto">AMP automatique</option>
          <option value="off">Désactivée</option>
        </select></label
      >
      <div class="wide">
        <p class="muted">
          Les 10 classes doivent être présentes dans le train et le split
          validation doit être non vide. Les labels issus des noms seuls sont
          interdits. Aucun téléchargement de poids préentraînés n’est lancé.
        </p>
        <PButton
          type="submit"
          label="Démarrer l’entraînement"
          icon="pi pi-play"
          :loading="busy"
        />
      </div>
    </form>
    <p v-if="datasets.error.value" class="notice error" role="alert">
      {{ datasets.error.value }}
    </p>
    <RouterLink v-if="datasets.data.value?.length === 0" to="/datasets"
      >Construire un premier dataset</RouterLink
    >
  </section>
  <TaskPanel
    v-if="selected && tasks.data.value?.some((task) => task.id === selected)"
    :key="selected"
    :id="selected"
    @completed="runs.refresh"
  />
  <section v-if="selected" class="panel">
    <h2>Progression par époque</h2>
    <p v-if="metrics.error.value" class="muted" role="status">
      Métriques pas encore disponibles : {{ metrics.error.value }}
    </p>
    <div v-if="metrics.data.value?.length" class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Phase</th>
            <th>Époque</th>
            <th>Perte train</th>
            <th>Accuracy validation</th>
            <th>Macro-F1 validation</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="epoch in metrics.data.value" :key="epoch.event_key">
            <td>{{ epoch.metrics.phase }}</td>
            <td>{{ epoch.metrics.epoch }}</td>
            <td>{{ epoch.metrics.train_loss.toFixed(4) }}</td>
            <td>{{ percent(epoch.metrics.validation.accuracy) }}</td>
            <td>{{ percent(epoch.metrics.validation.macro_f1) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="muted">
      Les mesures sont publiées à la fin de chaque époque réellement terminée.
    </p>
  </section>
  <section class="panel">
    <h2>Tâches d’entraînement</h2>
    <LoadState
      :error="tasks.error.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucun entraînement lancé depuis la console"
      @retry="tasks.refresh"
      ><ul class="plain-list">
        <li v-for="task in tasks.data.value" :key="task.id">
          <button class="text-button" @click="select(task.id)">
            {{ task.request.model_name }} · {{ task.id.slice(0, 8) }}</button
          ><span>{{ date(task.created_at) }}</span
          ><StatusBadge :status="task.status" />
        </li></ul
    ></LoadState>
    <h3>Runs et checkpoints existants</h3>
    <LoadState
      :error="runs.error.value"
      :empty="runs.data.value?.length === 0"
      empty-text="Aucun run enregistré"
      @retry="runs.refresh"
      ><ul class="plain-list">
        <li v-for="run in runs.data.value" :key="run.run_id">
          <button class="text-button" @click="select(run.run_id)">
            {{ run.run_id }}</button
          ><span>{{ percent(run.metadata.best_macro_f1) }}</span
          ><StatusBadge :status="run.status" />
        </li></ul
    ></LoadState>
  </section>
</template>
