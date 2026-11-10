<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, apiUrl, date, message, post, useResource } from "../api";
import TerritorialReportView from "../components/TerritorialReport.vue";
import SourceText from "../components/SourceText.vue";
import { articleHref, sourceIndex } from "../source-links";
import DossierProgressView from "../components/DossierProgress.vue";
import type { DossierProgress } from "../dossier-progress";
import type { TerritorialReport } from "../territorial";
import VideoThumbnail from "../components/VideoThumbnail.vue";
import TerritorialContextView from "../components/TerritorialContext.vue";
import { useDataMode } from "../data/data-mode";
import { auth } from "../auth-state";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import "../styles/dossier-reader.css";
import {
  interventionLabels,
  type Intervention,
  type ParcelPrefill,
} from "../territorial-context";

defineProps<{ readOnly?: boolean }>();

interface Profile {
  area_m2: number | null;
  land_type: string;
  project_type: string;
  locality: string;
  details: string;
  interventions: Intervention[];
}
interface Video {
  video_id: string;
  filename: string;
  analysis_id?: string;
  analysis_status?: string;
  analysis_error?: string;
}
interface Result {
  territorial_report?: TerritorialReport;
  status: string;
  observation_summary: string;
  video_count: number;
  confirmed_species: Array<{ name: string; display_name: string }>;
  predicted_species: Array<{ name: string; display_name: string }>;
  recommendations: Array<{
    theme: string;
    title: string;
    action: string;
    citation: string | null;
    qualification?: string;
    evidence_quote?: string;
  }>;
  green_space: { message: string };
  next_steps?: string[];
  limitations?: string[];
  sources: Array<{
    citation: string;
    title: string;
    page: number;
    original_url: string;
  }>;
  videos: Array<Video & { annotated_video_url: string }>;
}
interface Corpus {
  actor: string;
  id: string;
  videos: Video[];
  profile: { revision: number; profile: Profile } | null;
  dossier: {
    progress?: DossierProgress;
    id: string;
    status: string;
    error: string | null;
    profile_revision: number;
    completed_video_count: number;
    video_count: number;
    videos: Video[];
    result: Result | null;
  } | null;
}
const route = useRoute();
const dataMode = useDataMode();
const source = computed(() => dataMode.sourceId.value);
const canLoad = computed(
  () =>
    !!auth.user &&
    (dataMode.isReal.value ||
      (auth.user.role === "admin" && route.path.startsWith("/admin/"))),
);
const id = computed(() => String(route.params.id || ""));
const corpora = useResource<
  Array<{ id: string; video_count: number; created_at: string }>
>(
  () => (canLoad.value && !id.value ? "/parcels/corpora" : null),
  6000,
  () => source.value,
);
const corpus = useResource<Corpus>(
  () => (canLoad.value && id.value ? `/parcels/corpora/${id.value}` : null),
  4000,
  () => source.value,
);
const options = useResource<{
  land_types: Record<string, string>;
  project_types: Record<string, string>;
}>(() => (canLoad.value ? "/parcels/options" : null));
const blank = (): Profile => ({
  area_m2: null,
  land_type: "",
  project_type: "",
  locality: "",
  details: "",
  interventions: [],
});
const form = ref<Profile>(blank());
const territory = ref<InstanceType<typeof TerritorialContextView>>();
const touched = new Set<string>();
const automatic = new Map<string, string | number>();
const prefill = ref<ParcelPrefill | null>(null);
const savedNotice = ref("");
function applyPrefill(value: ParcelPrefill) {
  prefill.value = value;
  for (const key of ["area_m2", "land_type", "locality"] as const) {
    const suggestion = value.values[key];
    if (
      !touched.has(key) &&
      (form.value[key] == null ||
        form.value[key] === "" ||
        (automatic.has(key) && form.value[key] === automatic.get(key)))
    ) {
      Object.assign(form.value, { [key]: suggestion ?? blank()[key] });
      if (suggestion == null) automatic.delete(key);
      else automatic.set(key, suggestion);
      dirty.value = true;
    }
  }
}
const revision = ref(0),
  initialized = ref(false),
  dirty = ref(false),
  busy = ref(false),
  error = ref("");
const dossier = computed(() => corpus.data.value?.dossier);
const sourceArticles = computed(() =>
  sourceIndex(dossier.value?.result?.sources ?? []),
);
watch([id, source], () => {
  initialized.value = false;
  dirty.value = false;
  revision.value = 0;
  form.value = blank();
  error.value = "";
  touched.clear();
  automatic.clear();
  prefill.value = null;
  savedNotice.value = "";
});
watch(
  () => corpus.data.value,
  (value) => {
    if (!initialized.value && value) {
      if (value.profile && !dirty.value) {
        form.value = { ...blank(), ...value.profile.profile };
        revision.value = value.profile.revision;
      }
      initialized.value = true;
    }
  },
);
const pending = computed(() =>
  ["waiting_analysis", "queued", "running"].includes(
    dossier.value?.status || "",
  ),
);
async function prepare(generate = true) {
  if (busy.value || !canLoad.value || (generate && pending.value)) return;
  const capturedId = id.value,
    capturedSource = source.value;
  busy.value = true;
  error.value = "";
  try {
    const saved = await api<{ revision: number }>(
      `/parcels/corpora/${capturedId}/profile`,
      {
        method: "PUT",
        body: JSON.stringify({
          ...form.value,
          expected_revision: revision.value,
        }),
      },
    );
    if (id.value !== capturedId || source.value !== capturedSource) return;
    revision.value = saved.revision;
    dirty.value = false;
    savedNotice.value = "Modifications enregistrées.";
    await territory.value?.reload();
    if (id.value !== capturedId || source.value !== capturedSource) return;
    if (!generate) {
      await corpus.reload();
      return;
    }
    await post(`/parcels/corpora/${capturedId}/dossiers`, {
      profile_revision: saved.revision,
    });
    await corpus.refresh();
  } catch (reason) {
    if (id.value === capturedId && source.value === capturedSource)
      error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
const labels: Record<string, string> = {
  queued: "En attente",
  running: "Analyse en cours",
  completed: "Analyse terminée",
  error: "Erreur",
  cancelled: "Annulée",
};
</script>

<template>
  <GlassPanel depth="page" class="dossier-reader" topography>
    <div class="page-heading">
      <div>
        <p class="eyebrow">UNE PARCELLE · PLUSIEURS VIDÉOS · UN DOSSIER</p>
        <h1>
          {{
            id ? "Le dossier de votre parcelle" : "Mes dossiers biodiversité"
          }}
        </h1>
        <p class="subtitle">
          Regroupez les vidéos d’une même parcelle et décrivez votre projet une
          seule fois.
        </p>
      </div>
      <RouterLink v-if="readOnly" class="button-link" to="/parcelles"
        >Retour aux dossiers</RouterLink
      >
      <RouterLink v-else class="button-link" to="/videos"
        >Choisir ou importer des vidéos</RouterLink
      >
    </div>
    <p v-if="!canLoad" class="notice">
      Mode démonstration : ouvrez un dossier en données réelles pour consulter
      IGN. Aucune requête territoriale n’est envoyée avec un identifiant de
      démonstration.
    </p>
    <template v-else-if="!id"
      ><LoadState
        :loading="corpora.loading.value && !corpora.data.value"
        :error="corpora.error.value"
        :empty="corpora.data.value?.length === 0"
        empty-text="Sélectionnez plusieurs vidéos dans la vidéothèque pour préparer votre premier dossier."
        @retry="corpora.refresh"
        ><section
          class="panel"
          v-for="item in corpora.data.value"
          :key="item.id"
        >
          <RouterLink :to="`/parcelles/${item.id}`"
            >Parcelle · {{ item.video_count }} vidéo(s)</RouterLink
          >
          <p class="muted">Créée le {{ date(item.created_at) }}</p>
        </section></LoadState
      ></template
    >
    <LoadState
      v-else
      :loading="corpus.loading.value && !corpus.data.value"
      :error="corpus.error.value"
      @retry="corpus.refresh"
    >
      <template v-if="corpus.data.value">
        <TerritorialContextView
          ref="territory"
          :key="source + ':' + id"
          :corpus-id="id"
          :owner="corpus.data.value.actor"
          :project-controls="false"
          @prefill="applyPrefill"
        />
        <section class="panel">
          <h2>1. Vos {{ corpus.data.value.videos.length }} vidéos</h2>
          <p>
            Les fichiers identiques sont regroupés. Les analyses déjà réussies
            sont réutilisées.
          </p>
          <ul class="plain-list">
            <li
              v-for="video in dossier?.videos || corpus.data.value.videos"
              :key="video.video_id"
            >
              <VideoThumbnail
                class="dossier-video-thumbnail"
                :source="
                  apiUrl(
                    `/console/videos/${encodeURIComponent(video.video_id)}/file`,
                  )
                "
                :label="`Miniature de ${video.filename}`"
              />
              <RouterLink
                :to="{
                  path: '/analyses',
                  query: {
                    video: video.video_id,
                    corpus: id,
                    ...(video.analysis_id ? { task: video.analysis_id } : {}),
                  },
                }"
                >{{ video.filename }}</RouterLink
              ><span v-if="video.analysis_status">{{
                labels[video.analysis_status] || video.analysis_status
              }}</span>
              <p v-if="video.analysis_error" class="notice error">
                {{ video.analysis_error }}
              </p>
            </li>
          </ul>
        </section>
        <section class="panel">
          <h2>2. Votre parcelle et votre projet</h2>
          <p>
            La carte propose les informations disponibles en open data.
            Vérifiez-les et corrigez librement chaque champ, même si une valeur
            a déjà été récupérée.
          </p>
          <p v-if="prefill" class="notice">
            {{
              Object.keys(prefill.values).length
                ? "Informations disponibles proposées ci-dessous."
                : "Préremplissage indisponible ou incomplet : saisissez les informations manuellement."
            }}
            {{ prefill.notice }}
            <span v-if="prefill.retrieved_at"
              >Consultation : {{ date(prefill.retrieved_at) }}.</span
            >
          </p>
          <dl v-if="readOnly">
            <dt>Surface</dt>
            <dd>
              {{
                form.area_m2 == null ? "Non renseignée" : `${form.area_m2} m²`
              }}
            </dd>
            <dt>Type de parcelle</dt>
            <dd>
              {{
                options.data.value?.land_types[form.land_type] ||
                form.land_type ||
                "Non renseigné"
              }}
            </dd>
            <dt>Projet</dt>
            <dd>
              {{
                options.data.value?.project_types[form.project_type] ||
                form.project_type ||
                "Non renseigné"
              }}
            </dd>
            <dt>Commune ou secteur</dt>
            <dd>{{ form.locality || "Non renseigné" }}</dd>
            <dt>Précisions</dt>
            <dd>{{ form.details || "Non renseignées" }}</dd>
          </dl>
          <form
            v-else
            class="form-grid"
            @submit.prevent="prepare(true)"
            @input="dirty = true"
            @change="dirty = true"
          >
            <label
              >Surface de la parcelle (m²)<input
                v-model.number="form.area_m2"
                :disabled="busy"
                @input="touched.add('area_m2')"
                type="number"
                min="0.01"
                max="1000000000"
                step="any"
                required
            /></label>
            <label
              >Type de parcelle<select
                aria-label="Type de parcelle"
                v-model="form.land_type"
                :disabled="busy"
                required
                @change="touched.add('land_type')"
              >
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
              >Projet souhaité<select
                v-model="form.project_type"
                :disabled="busy"
                aria-label="Projet souhaité"
                required
              >
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
              >Commune ou secteur (modifiable)<input
                v-model="form.locality"
                :disabled="busy"
                @input="touched.add('locality')"
                maxlength="200"
                autocomplete="address-level2"
            /></label>
            <fieldset :disabled="busy">
              <legend>Interventions envisagées</legend>
              <label
                v-for="(label, code) in interventionLabels"
                :key="code"
                class="parcel-intervention"
                ><input
                  v-model="form.interventions"
                  type="checkbox"
                  :value="code"
                />{{ label }}</label
              >
            </fieldset>
            <details>
              <summary>Préciser le projet (facultatif)</summary>
              <label
                >Vos précisions<textarea
                  v-model="form.details"
                  :disabled="busy"
                  maxlength="1000"
                  rows="3"
                />
              </label>
            </details>
            <p
              v-if="options.error.value || error"
              role="alert"
              class="notice error"
            >
              {{ error || options.error.value }}
            </p>
            <p
              v-if="dossier && (dirty || dossier.profile_revision !== revision)"
              class="notice"
            >
              Le projet a changé : actualisez le dossier pour intégrer ces
              informations.
            </p>
            <PButton
              type="submit"
              :label="
                dossier
                  ? 'Actualiser mon dossier'
                  : 'Analyser les vidéos et préparer mon dossier'
              "
              :loading="busy"
              :disabled="
                busy || pending || !initialized || !!options.error.value
              "
            />
            <PButton
              type="button"
              label="Enregistrer mes modifications"
              :disabled="busy || !initialized"
              :loading="busy"
              @click="prepare(false)"
            />
            <p v-if="savedNotice" role="status">{{ savedNotice }}</p>
          </form>
        </section>
        <section
          v-if="dossier"
          class="panel parcel-dossier"
          aria-label="Dossier du corpus"
        >
          <h2>3. Vos résultats et votre dossier</h2>
          <p v-if="dossier.status === 'waiting_analysis'" role="status">
            {{ dossier.completed_video_count }} /
            {{ dossier.video_count }} vidéos analysées. Le dossier sera préparé
            quand toutes seront terminées. Vous pouvez fermer cette page.
          </p>
          <p
            v-if="['queued', 'running'].includes(dossier.status)"
            role="status"
          >
            {{
              dossier.status === "queued"
                ? "Votre dossier est dans la file d’attente."
                : "Préparation de la synthèse et recherche des sources en cours…"
            }}
          </p>
          <p
            v-if="dossier.status === 'error'"
            role="alert"
            class="notice error"
          >
            {{ dossier.error }} Vous pouvez relancer la préparation ; les
            analyses réussies seront conservées.
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
            <a
              class="button-link"
              :href="apiUrl(`/parcels/dossiers/${dossier.id}/export`)"
              download
              >Télécharger mon dossier commun (.txt)</a
            >
            <p>{{ dossier.result.observation_summary }}</p>
            <p>
              Corpus de {{ dossier.result.video_count }} vidéos. Les passages
              répétés ne constituent pas un décompte d’individus.
            </p>
            <ul class="plain-list">
              <li v-for="s in dossier.result.confirmed_species" :key="s.name">
                {{ s.display_name }} · confirmé
              </li>
              <li v-for="s in dossier.result.predicted_species" :key="s.name">
                {{ s.display_name }} · à confirmer
              </li>
            </ul>
            <h3>Vidéos annotées</h3>
            <ul>
              <li v-for="video in dossier.result.videos" :key="video.video_id">
                <a :href="apiUrl(video.annotated_video_url)" download
                  >{{ video.filename }} · MP4 annoté</a
                >
              </li>
            </ul>
            <p
              v-if="dossier.result.status === 'insufficient_sources'"
              class="notice"
            >
              Les documents disponibles sont insuffisants pour proposer des
              mesures spécifiques. Le dossier indique les observations et les
              informations à compléter.
            </p>
            <details
              v-for="card in dossier.result.recommendations"
              :key="card.theme"
            >
              <summary>
                {{ card.title
                }}{{ card.citation ? " · piste sourcée" : " · à documenter" }}
              </summary>
              <p>{{ card.action }}</p>
              <p v-if="card.qualification" class="muted">
                {{ card.qualification }}
              </p>
              <blockquote v-if="card.evidence_quote">
                {{ card.evidence_quote }}
                <SourceText
                  :text="`[${card.citation}]`"
                  :sources="sourceArticles"
                />
              </blockquote>
            </details>
            <details class="dossier-audit">
              <summary>Toutes les sorties du dossier (JSON)</summary>
              <p>
                Résultats enregistrés, références et métadonnées produits pour
                ce dossier.
              </p>
              <pre>{{ JSON.stringify(dossier.result, null, 2) }}</pre>
              <a
                :href="
                  apiUrl(`/parcels/dossiers/${dossier.id}/export?format=json`)
                "
                download
                >Télécharger toutes les sorties</a
              >
            </details>
            <section v-if="dossier.result.next_steps?.length">
              <h3>Prochaines étapes</h3>
              <ul>
                <li v-for="step in dossier.result.next_steps" :key="step">
                  {{ step }}
                </li>
              </ul>
            </section>
            <section v-if="dossier.result.limitations?.length">
              <h3>Limites du dossier</h3>
              <ul>
                <li v-for="limit in dossier.result.limitations" :key="limit">
                  {{ limit }}
                </li>
              </ul>
            </section>
            <details>
              <summary>Part de terrain vert</summary>
              <p>{{ dossier.result.green_space.message }}</p>
            </details>
            <details>
              <summary>Sources utilisées</summary>
              <ul>
                <li
                  v-for="source in dossier.result.sources"
                  :key="source.citation"
                >
                  <a
                    :href="articleHref(source) ?? undefined"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ source.title }}</a
                  >
                  — page {{ source.page }}
                </li>
              </ul>
            </details>
            <p class="muted">
              Après une confirmation d’espèce dans une vidéo, actualisez le
              dossier pour en tenir compte.
            </p>
          </template>
        </section>
        <p v-else class="notice">
          Aucun dossier n’a encore été généré pour cette parcelle.
        </p>
      </template>
    </LoadState>
  </GlassPanel>
</template>
