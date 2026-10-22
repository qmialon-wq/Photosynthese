<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, apiUrl, date, message, percent, post, useResource } from "../api";
import BoxEditor from "../components/BoxEditor.vue";
import type { Box, Sample, Species } from "../types";
const route = useRoute();
const state = ref("pending"),
  species = ref(""),
  quality = ref(""),
  offset = ref(0);
const samples = useResource<Sample[]>(
  () =>
    `/review/samples?limit=24&offset=${offset.value}&state=${state.value}${species.value ? `&label=${species.value}` : ""}${quality.value ? `&quality=${quality.value}` : ""}${route.query.video_id ? `&video_id=${route.query.video_id}` : ""}`,
  5000,
);
const classes = useResource<Species[]>(() => "/review/species");
const selected = ref<Sample | null>(null),
  box = ref<Box>({ x: 0, y: 0, w: 1, h: 1 }),
  label = ref(""),
  reason = ref(""),
  error = ref(""),
  success = ref(""),
  busy = ref(false);
const history = ref<Array<Sample>>([]);
watch([state, species, quality], () => {
  offset.value = 0;
});
async function open(sample: Sample) {
  selected.value = sample;
  box.value = { ...sample.box };
  label.value = sample.label || "";
  reason.value = "";
  error.value = "";
  history.value = [];
  try {
    history.value = await api(`/review/samples/${sample.id}/history`);
  } catch (reason) {
    error.value = message(reason);
  }
}
async function decide(decision: "validate" | "reject" | "reopen") {
  if (!selected.value) return;
  busy.value = true;
  error.value = "";
  try {
    const payload = {
      expected_revision: selected.value.revision,
      decision,
      reason: reason.value,
      ...(decision === "validate"
        ? { label: label.value, box: box.value }
        : {}),
      provenance: { outil: "console-web" },
    };
    await post(`/review/samples/${selected.value.id}/decisions`, payload);
    selected.value = null;
    success.value =
      decision === "reject"
        ? "Exemple rejeté et exclu des prochains datasets."
        : "Décision enregistrée. Un recadrage corrigé peut être en cours de rendu.";
    await samples.refresh();
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
      <p class="eyebrow">UNE DÉCISION HUMAINE, UNE DONNÉE FIABLE</p>
      <h1>Validation humaine</h1>
      <p class="subtitle">
        Vérifiez l’espèce, ajustez le cadre, conservez la provenance.
      </p>
    </div>
    <PButton
      icon="pi pi-refresh"
      label="Actualiser"
      severity="secondary"
      @click="samples.refresh"
    />
  </div>
  <p v-if="success" class="notice success" role="status">{{ success }}</p>
  <p v-if="route.query.video_id" class="notice">
    Recadrages de la vidéo sélectionnée.
    <RouterLink to="/review">Afficher toute la file</RouterLink>
  </p>
  <section class="panel">
    <div class="toolbar">
      <select v-model="state" aria-label="État de validation">
        <option value="pending">À revoir</option>
        <option value="validated">Validés</option>
        <option value="corrected">Corrigés</option>
        <option value="rejected">Rejetés</option></select
      ><select v-model="species" aria-label="Filtrer par espèce">
        <option value="">Toutes les espèces</option>
        <option
          v-for="item in classes.data.value"
          :value="item.name"
          :key="item.name"
        >
          {{ item.name }}
        </option></select
      ><select v-model="quality" aria-label="Qualité des images">
        <option value="">Toutes les qualités</option>
        <option value="blurry">Floues</option>
        <option value="too_small">Trop petites</option>
        <option value="near_duplicate">Quasi identiques</option></select
      ><span class="muted">Priorité : rareté et incertitude</span>
    </div>
    <LoadState
      :error="samples.error.value"
      :loading="samples.loading.value && !samples.data.value"
      :empty="samples.data.value?.length === 0"
      empty-text="Aucun recadrage dans cette sélection"
      @retry="samples.refresh"
      ><div class="crop-grid">
        <button
          v-for="sample in samples.data.value"
          :key="sample.id"
          class="crop-card"
          :aria-label="`Revoir ${sample.original_name}, révision ${sample.revision}`"
          @click="open(sample)"
        >
          <img
            :src="
              apiUrl(
                `/review/samples/${sample.id}/images/${sample.render_status === 'ready' ? 'crop' : 'initial_crop'}?revision=${sample.revision}`,
              )
            "
            :alt="`Animal proposé : ${sample.label || sample.predicted_label || sample.species_candidate || 'non identifié'}`"
            loading="lazy"
          />
          <div>
            <div class="section-head">
              <StatusBadge :status="sample.state" /><small
                >{{ sample.split
                }}{{ sample.test_locked ? " · gelé" : "" }}</small
              >
            </div>
            <h3>
              {{
                sample.label ||
                sample.predicted_label ||
                sample.species_candidate ||
                "Espèce à identifier"
              }}
            </h3>
            <p class="muted">{{ sample.original_name }}</p>
            <small
              >Détection {{ percent(sample.detection_score) }} · Classification
              {{ percent(sample.classification_score) }}</small
            >
            <div class="quality-flags">
              <span v-if="sample.quality?.blurry">Flou</span
              ><span v-if="sample.quality?.too_small">Petit</span
              ><span v-if="sample.frame_quality.near_duplicate">Similaire</span
              ><span v-if="sample.render_status !== 'ready'"
                >Rendu {{ sample.render_status }}</span
              >
            </div>
          </div>
        </button>
      </div></LoadState
    >
    <div class="pagination">
      <PButton
        label="Précédent"
        :disabled="offset === 0"
        severity="secondary"
        @click="offset = Math.max(0, offset - 24)"
      /><span>Page {{ offset / 24 + 1 }}</span
      ><PButton
        label="Suivant"
        :disabled="(samples.data.value?.length ?? 0) < 24"
        severity="secondary"
        @click="offset += 24"
      />
    </div>
  </section>
  <PDialog
    :visible="!!selected"
    header="Vérifier l’annotation"
    modal
    :closable="!busy"
    :style="{ width: 'min(1140px,96vw)' }"
    @update:visible="selected = null"
    ><template v-if="selected"
      ><p v-if="selected.test_locked" class="notice">
        Ce groupe de test est gelé. Ses annotations ne peuvent plus être
        modifiées.
      </p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <div class="review-layout">
        <BoxEditor
          v-model="box"
          :src="apiUrl(`/review/samples/${selected.id}/images/original`)"
          :disabled="selected.test_locked || busy"
        />
        <form class="form-grid" @submit.prevent="decide('validate')">
          <div>
            <StatusBadge :status="selected.state" />
            <p>{{ selected.original_name }}</p>
            <small
              >Révision {{ selected.revision }} · {{ selected.split }}</small
            >
          </div>
          <label
            >Espèce confirmée<select
              v-model="label"
              required
              :disabled="selected.test_locked"
            >
              <option value="" disabled>
                Choisir explicitement une espèce
              </option>
              <option
                v-for="item in classes.data.value"
                :key="item.name"
                :value="item.name"
              >
                {{ item.name }}
              </option>
            </select></label
          >
          <p class="muted">
            Suggestion non validée :
            {{
              selected.predicted_label || selected.species_candidate || "Aucune"
            }}
          </p>
          <label
            >Motif de la décision<textarea
              v-model="reason"
              required
              maxlength="1000"
              rows="3"
              :disabled="selected.test_locked"
              placeholder="Ce qui a été vérifié ou corrigé"
            /></label
          ><PButton
            type="submit"
            label="Confirmer l’annotation"
            icon="pi pi-check"
            :loading="busy"
            :disabled="selected.test_locked || !label || !reason.trim()"
          /><PButton
            label="Rejeter cet exemple"
            icon="pi pi-times"
            severity="danger"
            outlined
            :disabled="busy || selected.test_locked || !reason.trim()"
            @click="decide('reject')"
          /><PButton
            v-if="selected.state !== 'pending'"
            label="Remettre à revoir"
            severity="secondary"
            :disabled="busy || selected.test_locked || !reason.trim()"
            @click="decide('reopen')"
          /><PButton
            label="Fermer sans enregistrer"
            severity="secondary"
            text
            :disabled="busy"
            @click="selected = null"
          />
        </form>
      </div>
      <details>
        <summary>Historique des corrections</summary>
        <ol class="history">
          <li v-for="entry in history" :key="entry.revision">
            <strong>Révision {{ entry.revision }} · {{ entry.actor }}</strong
            ><span
              >{{ date(entry.created_at) }} · {{ entry.state }} ·
              {{ entry.label || "Sans label validé" }}</span
            >
            <p>{{ entry.provenance.reason || "Création du recadrage" }}</p>
          </li>
        </ol>
      </details></template
    ></PDialog
  >
</template>
