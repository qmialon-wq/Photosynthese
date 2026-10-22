<script setup lang="ts">
import { ref } from "vue";
import { date, message, percent, post, useResource } from "../api";
import type { Model, Operation } from "../types";
const models = useResource<Model[]>(() => "/console/models", 5000);
const name = ref(""),
  checkpoint = ref("classifier_v3_best.pt"),
  taskId = ref(""),
  error = ref(""),
  busy = ref(false),
  pending = ref<Model | null>(null);
async function register() {
  busy.value = true;
  error.value = "";
  try {
    taskId.value = (
      await post<Operation>("/console/models", {
        name: name.value,
        checkpoint_key: checkpoint.value,
      })
    ).id;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function activate() {
  if (!pending.value) return;
  busy.value = true;
  error.value = "";
  try {
    await post(`/console/models/${pending.value.id}/activate`);
    pending.value = null;
    await models.refresh();
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
      <p class="eyebrow">REGISTRE LOCAL · CHECKPOINTS VÉRIFIÉS</p>
      <h1>Modèles</h1>
      <p class="subtitle">
        Comparez les versions et choisissez le classificateur des prochaines
        analyses.
      </p>
    </div>
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <section class="panel">
    <h2>Enregistrer un checkpoint existant</h2>
    <form class="inline-form" @submit.prevent="register">
      <label
        >Nom du modèle<input
          v-model="name"
          required
          maxlength="100"
          placeholder="Classificateur Normandie V3" /></label
      ><label
        >Chemin relatif à data/checkpoints<input
          v-model="checkpoint"
          required
          placeholder="run-id/best.pt" /></label
      ><PButton
        type="submit"
        label="Vérifier et enregistrer"
        icon="pi pi-plus"
        :loading="busy"
      />
    </form>
    <p class="muted">
      Le worker vérifie le fichier, les 10 classes, leur ordre et la
      compatibilité des poids. Un entraînement terminé enregistre son meilleur
      checkpoint, sans l’activer automatiquement.
    </p>
  </section>
  <TaskPanel v-if="taskId" :id="taskId" @completed="models.refresh" />
  <LoadState
    :loading="models.loading.value && !models.data.value"
    :error="models.error.value"
    :empty="models.data.value?.length === 0"
    empty-text="Aucun modèle enregistré"
    @retry="models.refresh"
    ><div class="model-grid">
      <article
        class="panel model-card"
        v-for="model in models.data.value"
        :key="model.id"
      >
        <div class="section-head">
          <span class="model-icon"><i class="pi pi-box" /></span
          ><PTag
            v-if="model.active"
            severity="success"
            value="Modèle actif"
          /><PTag
            v-else
            severity="secondary"
            :value="
              model.status === 'validated'
                ? 'Validé'
                : model.status === 'archived'
                  ? 'Archivé'
                  : 'Candidat à comparer'
            "
          />
        </div>
        <h2>{{ model.name }}</h2>
        <p class="muted">
          {{ model.metadata.model_name }} · {{ model.metadata.image_size }} px
        </p>
        <div class="measure">
          <span>Macro-F1 de validation enregistré</span
          ><strong>{{
            percent(
              model.metrics.validation?.macro_f1 ?? model.metrics.macro_f1,
            )
          }}</strong>
        </div>
        <dl class="facts">
          <div>
            <dt>Enregistré le</dt>
            <dd>{{ date(model.created_at) }}</dd>
          </div>
          <div>
            <dt>Checkpoint</dt>
            <dd class="mono">{{ model.checkpoint_key }}</dd>
          </div>
          <div>
            <dt>SHA-256</dt>
            <dd class="mono">{{ model.sha256.slice(0, 20) }}…</dd>
          </div>
        </dl>
        <div class="actions">
          <PButton
            label="Définir comme actif"
            :disabled="model.active || busy || model.status !== 'validated'"
            severity="secondary"
            @click="pending = model"
          /><RouterLink
            :to="{ path: '/evaluation', query: { model: model.id } }"
            >Métriques <i class="pi pi-arrow-up-right"
          /></RouterLink>
        </div>
      </article></div
  ></LoadState>
  <p class="notice">
    Les candidats nécessitent une comparaison sur validation humaine avant
    promotion. Les opérations de comparaison, promotion justifiée et historique
    sont disponibles dans l’API /classification (documentation /api/docs).
  </p>
  <PDialog
    :visible="!!pending"
    header="Changer le modèle actif"
    modal
    :style="{ width: 'min(480px,95vw)' }"
    @update:visible="pending = null"
    ><p>
      Utiliser « {{ pending?.name }} » pour les prochaines analyses classifiées
      ? Les tâches déjà soumises conservent leur version.
    </p>
    <template #footer
      ><PButton
        label="Annuler"
        severity="secondary"
        @click="pending = null" /><PButton
        label="Confirmer le modèle actif"
        :loading="busy"
        @click="activate" /></template
  ></PDialog>
</template>
