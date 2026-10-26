<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { api, apiUrl, message, post, useResource } from "../api";
import TerritorialReportView from "./TerritorialReport.vue";
import DossierProgressView from "./DossierProgress.vue";
import type { DossierProgress } from "../dossier-progress";
import type { TerritorialReport } from "../territorial";

interface Profile {
  area_m2: number | null;
  land_type: string;
  project_type: string;
  locality: string;
  details: string;
}
interface Source {
  citation: string;
  title: string;
  doi: string | null;
  page: number;
  original_url: string;
  text: string;
}
interface Dossier {
  progress?: DossierProgress;
  id: string;
  status: string;
  error: string | null;
  profile_revision: number;
  result: null | {
    territorial_report?: TerritorialReport;
    status: string;
    observation_summary: string;
    green_space: { message: string };
    confirmed_species: Array<{ name: string; display_name: string }>;
    predicted_species: Array<{
      name: string;
      display_name: string;
      score: number;
    }>;
    recommendations: Array<{
      theme: string;
      title: string;
      status: string;
      action: string;
      qualification?: string;
      citation: string | null;
      evidence_quote?: string;
    }>;
    sources: Source[];
    next_steps: string[];
    limitations: string[];
  };
}
interface State {
  profile: { revision: number; profile: Profile } | null;
  dossier: Dossier | null;
}
const props = defineProps<{
  videoId: string;
  analysisId: string;
  completed: boolean;
}>();
const enabled = ref(true),
  revision = ref(0),
  dirty = ref(false),
  error = ref(""),
  busy = ref(false);
const form = ref<Profile>({
  area_m2: null,
  land_type: "",
  project_type: "",
  locality: "",
  details: "",
});
const state = useResource<State>(
  () =>
    props.videoId
      ? `/parcels/videos/${encodeURIComponent(props.videoId)}${props.analysisId ? `?analysis_id=${encodeURIComponent(props.analysisId)}` : ""}`
      : null,
  4000,
);
const dossier = computed(() => state.data.value?.dossier);
const options = useResource<{
  land_types: Record<string, string>;
  project_types: Record<string, string>;
}>(() => "/parcels/options");
const initialized = ref(false);
watch(
  () => props.videoId,
  () => {
    initialized.value = false;
    dirty.value = false;
    revision.value = 0;
    form.value = {
      area_m2: null,
      land_type: "",
      project_type: "",
      locality: "",
      details: "",
    };
  },
);
watch(
  () => state.data.value,
  (value) => {
    if (!initialized.value && value) {
      if (value.profile && !dirty.value) {
        form.value = { ...value.profile.profile };
        revision.value = value.profile.revision;
      }
      initialized.value = true;
    }
  },
);
async function save(): Promise<number | null> {
  if (!enabled.value) return null;
  if (state.loading.value && !initialized.value)
    throw new Error("Chargement de la parcelle en cours.");
  if (state.error.value) throw new Error(state.error.value);
  const result = await api<{ revision: number }>(
    `/parcels/videos/${encodeURIComponent(props.videoId)}`,
    {
      method: "PUT",
      body: JSON.stringify({
        ...form.value,
        expected_revision: revision.value,
      }),
    },
  );
  revision.value = result.revision;
  dirty.value = false;
  return result.revision;
}
async function refreshDossier() {
  busy.value = true;
  error.value = "";
  try {
    const saved = await save();
    if (saved === null) return;
    await post(
      `/parcels/videos/${encodeURIComponent(props.videoId)}/dossiers`,
      { analysis_id: props.analysisId, profile_revision: saved },
    );
    await state.refresh();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
defineExpose({ save });
</script>

<template>
  <fieldset class="parcel-questionnaire">
    <legend>Votre parcelle et votre projet</legend>
    <label class="inline-check"
      ><input type="checkbox" v-model="enabled" /> Recevoir mon dossier
      biodiversité</label
    >
    <p class="muted">
      Trois informations pour préparer des pistes d’aménagement avec la vidéo
      annotée.
    </p>
    <LoadState
      :error="state.error.value || options.error.value"
      :loading="state.loading.value && !initialized"
      @retry="state.refresh"
    />
    <div
      v-if="enabled"
      class="form-grid"
      @input="dirty = true"
      @change="dirty = true"
    >
      <label
        >Surface de la parcelle (m²)<input
          v-model.number="form.area_m2"
          type="number"
          min="0.01"
          max="1000000000"
          step="any"
          required
          placeholder="Ex. 2500"
      /></label>
      <label
        >Type de parcelle<select v-model="form.land_type" required>
          <option disabled value="">Choisir le terrain</option>
          <option
            v-for="(label, key) in options.data.value?.land_types"
            :key="key"
            :value="key"
          >
            {{ label }}
          </option>
        </select></label
      >
      <label
        >Projet souhaité<select v-model="form.project_type" required>
          <option disabled value="">Choisir votre projet</option>
          <option
            v-for="(label, key) in options.data.value?.project_types"
            :key="key"
            :value="key"
          >
            {{ label }}
          </option>
        </select></label
      >
      <label
        >Commune ou secteur (facultatif)<input
          v-model="form.locality"
          maxlength="200"
          autocomplete="address-level2"
          placeholder="Ex. Caen"
      /></label>
      <details>
        <summary>Préciser le projet (facultatif)</summary>
        <label
          >Vos précisions<textarea
            v-model="form.details"
            maxlength="1000"
            rows="3"
            placeholder="Usages, éléments à conserver, contraintes…"
          />
        </label>
      </details>
    </div>
    <p v-if="error" role="alert" class="notice error">{{ error }}</p>
    <p
      v-if="dossier && (dirty || dossier.profile_revision !== revision)"
      class="notice"
    >
      Formulaire modifié : actualisez le dossier pour prendre en compte ces
      informations.
    </p>
    <section
      v-if="dossier"
      aria-label="Dossier biodiversité"
      class="parcel-dossier"
    >
      <h3>Votre dossier biodiversité</h3>
      <p
        v-if="
          ['waiting_analysis', 'queued', 'running'].includes(dossier.status)
        "
        role="status"
      >
        {{
          dossier.status === "waiting_analysis"
            ? "Le dossier sera préparé après l’analyse vidéo."
            : dossier.status === "queued"
              ? "Votre dossier est dans la file d’attente. Vous pouvez quitter cette page."
              : "Lecture du corpus documentaire et rédaction du rapport en cours…"
        }}
      </p>
      <p v-if="dossier.status === 'error'" class="notice error" role="alert">
        {{
          dossier.error ||
          "La préparation du dossier a échoué. Vous pouvez la relancer."
        }}
      </p>
      <DossierProgressView
        v-if="['queued', 'running'].includes(dossier.status)"
        :progress="dossier.progress"
      />
      <template v-if="dossier.status === 'completed' && dossier.result">
        <TerritorialReportView
          v-if="dossier.result.territorial_report"
          :report="dossier.result.territorial_report"
          :dossier-id="dossier.id"
        />
        <div class="actions">
          <a
            class="button-link"
            :href="apiUrl(`/parcels/dossiers/${dossier.id}/export`)"
            download
            >Télécharger mon dossier (.txt)</a
          ><a
            :href="apiUrl(`/console/tasks/${analysisId}/artifacts/video`)"
            download
            >Vidéo annotée (.mp4)</a
          >
        </div>
        <p>{{ dossier.result.observation_summary }}</p>
        <ul class="plain-list">
          <li v-for="item in dossier.result.confirmed_species" :key="item.name">
            {{ item.display_name }} · confirmé
          </li>
          <li v-for="item in dossier.result.predicted_species" :key="item.name">
            {{ item.display_name }} · à confirmer
          </li>
        </ul>
        <p
          v-if="dossier.result.status === 'insufficient_sources'"
          class="notice"
        >
          Les sources validées sont insuffisantes pour proposer des mesures
          spécifiques. Le dossier indique les observations et les informations à
          compléter.
        </p>
        <details
          v-for="item in dossier.result.territorial_report
            ? []
            : dossier.result.recommendations"
          :key="item.theme"
        >
          <summary>
            {{ item.title
            }}{{ item.citation ? " · piste sourcée" : " · à documenter" }}
          </summary>
          <p>{{ item.action }}</p>
          <p v-if="item.qualification" class="muted">
            {{ item.qualification }}
          </p>
          <blockquote v-if="item.evidence_quote">
            {{ item.evidence_quote }} [{{ item.citation }}]
          </blockquote>
        </details>
        <details>
          <summary>Part de terrain vert</summary>
          <p>{{ dossier.result.green_space.message }}</p>
        </details>
        <details>
          <summary>
            Sources utilisées ({{ dossier.result.sources.length }})
          </summary>
          <ul>
            <li v-for="source in dossier.result.sources" :key="source.citation">
              [{{ source.citation }}] {{ source.title }} — page
              {{ source.page }}
              <a
                :href="apiUrl(source.original_url)"
                target="_blank"
                rel="noopener"
                >Lire l’original</a
              >
            </li>
          </ul>
        </details>
      </template>
    </section>
    <PButton
      type="button"
      v-if="completed && enabled"
      :label="dossier ? 'Actualiser mon dossier' : 'Préparer mon dossier'"
      severity="secondary"
      :loading="busy"
      :disabled="
        busy ||
        ['waiting_analysis', 'queued', 'running'].includes(
          dossier?.status ?? '',
        )
      "
      @click="refreshDossier"
    />
    <p class="muted" v-if="completed">
      Après une validation d’espèce, actualisez le dossier pour intégrer la
      confirmation.
    </p>
  </fieldset>
</template>
