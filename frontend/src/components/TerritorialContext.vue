<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { api, apiUrl, date, message, useResource } from "../api";
import { auth } from "../auth-state";
import { useDataMode } from "../data/data-mode";
import {
  interventionLabels,
  type Intervention,
  type TerritorialContext,
} from "../territorial-context";
import ProjectAlternatives from "./ProjectAlternatives.vue";
import TerritorialPointMap from "./TerritorialPointMap.vue";

const props = defineProps<{ corpusId: string; owner: string }>();
const store = useDataMode();
const real = computed(() => store.isReal.value && !!auth.user);
const writable = computed(
  () =>
    real.value &&
    (props.owner === auth.user?.id || auth.user?.role === "admin"),
);
const base = computed(() => `/parcels/corpora/${props.corpusId}`);
const state = useResource<TerritorialContext>(
  () => (real.value ? base.value + "/territorial-context" : null),
  3000,
  () => store.sourceId.value,
);
const context = computed(() => {
  const value = state.data.value;
  return value &&
    typeof value.profile === "object" &&
    value.profile !== null &&
    Number.isInteger(value.profile_revision) &&
    "query" in value
    ? value
    : null;
});
const latitude = ref<number | null>(null),
  longitude = ref<number | null>(null);
const provenance = ref<"numeric" | "map">("numeric");
const locationRevision = ref(0),
  profileRevision = ref(0);
const interventions = ref<Intervention[]>([]);
const locationDirty = ref(false),
  projectDirty = ref(false),
  busy = ref(false),
  error = ref("");
const query = computed(() => context.value?.query);
const result = computed(() => query.value?.result);
const documentaryLabel = computed(() => {
  const task = query.value?.documentary_task;
  if (!task) return "";
  if (task.status === "error") return "Recherche documentaire indisponible";
  const status = task.result?.status;
  if (status === "no_sources")
    return "Aucun extrait admissible pertinent disponible";
  if (status === "candidates_archived")
    return "Extraits disponibles dans une révision complémentaire";
  if (status === "superseded")
    return "Une consultation plus récente a été conservée";
  return "Recherche documentaire locale en cours";
});
const groups = [
  { code: "avoid", label: "Éviter" },
  { code: "reduce", label: "Réduire" },
  { code: "investigate", label: "À approfondir" },
] as const;
const kindLabels: Record<string, string> = {
  user_declaration: "Déclaration du projet",
  human_observation: "Observation humaine",
  map_result: "Résultat cartographique",
};
const statusLabels: Record<string, string> = {
  success: "Intersection au point",
  empty: "Aucun zonage renvoyé au point",
  unavailable: "Indisponible",
  error: "Erreur",
  pending: "Consultation en attente",
  complete: "Consultation complète",
  partial: "Consultation partielle",
  failed: "Consultation en échec",
};
watch(
  () => context.value,
  (value) => {
    if (!value) return;
    if (!locationDirty.value) {
      latitude.value = value.location?.latitude ?? null;
      longitude.value = value.location?.longitude ?? null;
      locationRevision.value = value.location?.revision ?? 0;
      provenance.value = value.location?.provenance ?? "numeric";
    }
    if (!projectDirty.value) {
      interventions.value = [...(value.profile.interventions ?? [])];
      profileRevision.value = value.profile_revision;
    }
  },
);
function selectPoint(lat: number, lon: number) {
  latitude.value = lat;
  longitude.value = lon;
  provenance.value = "map";
  locationDirty.value = true;
}
async function perform(operation: () => Promise<void>) {
  if (!writable.value || busy.value) return;
  const source = store.sourceId.value,
    corpus = props.corpusId;
  busy.value = true;
  error.value = "";
  try {
    await operation();
  } catch (reason) {
    if (source === store.sourceId.value && corpus === props.corpusId)
      error.value = message(reason);
  } finally {
    if (source === store.sourceId.value && corpus === props.corpusId)
      busy.value = false;
  }
}
function reloadDraft() {
  locationDirty.value = false;
  projectDirty.value = false;
  error.value = "";
  void state.reload();
}
function saveLocation() {
  return perform(async () => {
    await api(base.value + "/location", {
      method: "PUT",
      body: JSON.stringify({
        latitude: latitude.value,
        longitude: longitude.value,
        provenance: provenance.value,
        expected_revision: locationRevision.value,
      }),
    });
    locationDirty.value = false;
    await state.reload();
  });
}
function saveProject() {
  return perform(async () => {
    await api(base.value + "/profile", {
      method: "PUT",
      body: JSON.stringify({
        interventions: interventions.value,
        expected_revision: profileRevision.value,
      }),
    });
    projectDirty.value = false;
    await state.reload();
  });
}
function consult() {
  return perform(async () => {
    await api(base.value + "/territorial-queries", {
      method: "POST",
      body: JSON.stringify({
        expected_location_revision: context.value?.location?.revision,
        expected_profile_revision: context.value?.profile_revision,
      }),
    });
    await state.reload();
  });
}
</script>

<template>
  <section
    class="panel territorial-context"
    aria-label="Analyse préliminaire du projet"
  >
    <p class="eyebrow">CONTEXTE TERRITORIAL · AIDE À L’AMÉNAGEMENT</p>
    <h2>Analyse préliminaire du projet</h2>
    <p>
      Faits enregistrés, propositions conditionnelles et vérifications
      nécessaires sont présentés séparément.
    </p>
    <p v-if="!real" class="notice">
      Mode démonstration : aucune consultation territoriale réelle n’est
      envoyée. Passez aux données réelles pour localiser votre dossier.
    </p>
    <template v-else>
      <p v-if="state.error.value" class="notice error" role="alert">
        {{ state.error.value }}
        <button class="button-link" type="button" @click="state.refresh">
          Recharger
        </button>
      </p>
      <p v-if="error" role="alert" class="notice error">
        {{ error }} En cas de conflit, rechargez le dossier avant de réessayer.
        <button class="button-link" type="button" @click="reloadDraft">
          Recharger les valeurs enregistrées
        </button>
      </p>
      <p v-if="state.data.value && !context" class="notice error" role="alert">
        Contexte territorial invalide. Rechargez ou consultez l’administration.
      </p>
      <template v-if="context">
        <h3>1. Mon terrain</h3>
        <p>
          Le marqueur représente uniquement le point interrogé, sans contour
          parcellaire.
        </p>
        <TerritorialPointMap
          :latitude="latitude"
          :longitude="longitude"
          :disabled="!writable || busy"
          @select="selectPoint"
        />
        <form class="form-grid" @submit.prevent="saveLocation">
          <label
            >Latitude WGS84<input
              v-model.number="latitude"
              type="number"
              min="-90"
              max="90"
              step="any"
              required
              :disabled="!writable || busy"
              @input="
                locationDirty = true;
                provenance = 'numeric';
              "
          /></label>
          <label
            >Longitude WGS84<input
              v-model.number="longitude"
              type="number"
              min="-180"
              max="180"
              step="any"
              required
              :disabled="!writable || busy"
              @input="
                locationDirty = true;
                provenance = 'numeric';
              "
          /></label>
          <button
            class="button-link"
            v-if="writable"
            :disabled="busy"
            type="submit"
          >
            Enregistrer le point
          </button>
        </form>
        <p v-if="context.location" class="muted">
          Point enregistré · révision {{ context.location.revision }} ·
          {{ date(context.location.created_at) }} · saisie
          {{
            context.location.provenance === "map" ? "sur la carte" : "numérique"
          }}
        </p>
        <h3>2. Mon projet et les interventions prévues</h3>
        <p>
          {{ context.profile.locality || "Secteur non renseigné" }} ·
          {{
            context.profile.details ||
            "Aucune autre intervention décrite dans les précisions existantes."
          }}
        </p>
        <p v-if="!('interventions' in context.profile)" class="notice">
          Interventions non renseignées dans le profil historique.
        </p>
        <p v-else-if="!context.profile.interventions?.length" class="notice">
          Liste explicitement vide. Cela ne prouve pas l’absence de travaux.
        </p>
        <form @submit.prevent="saveProject">
          <fieldset :disabled="!writable || busy">
            <legend>Interventions facultatives</legend>
            <label
              v-for="(label, code) in interventionLabels"
              :key="code"
              class="intervention-choice"
            >
              <input
                v-model="interventions"
                type="checkbox"
                :value="code"
                @change="projectDirty = true"
              />
              {{ label }}
            </label>
          </fieldset>
          <p>
            Une case non cochée ne prouve pas l’absence de cette intervention.
            Enregistrer une liste vide efface explicitement les choix
            précédents.
          </p>
          <button
            class="button-link"
            v-if="writable"
            type="submit"
            :disabled="busy"
          >
            Enregistrer les interventions
          </button>
        </form>
        <h3>3. Observations humaines et données environnementales</h3>
        <p>
          Seules les observations validées ou corrigées humainement liées à ce
          dossier sont retenues. Les prédictions automatiques sont exclues.
        </p>
        <button
          class="button-link"
          v-if="writable"
          type="button"
          :disabled="
            busy ||
            !context.location ||
            locationDirty ||
            projectDirty ||
            query?.status === 'pending'
          "
          @click="consult"
        >
          Consulter les données territoriales et analyser le projet
        </button>
        <p v-if="locationDirty || projectDirty" class="notice">
          Enregistrez vos modifications avant de lancer une consultation. Les
          résultats ci-dessous concernent la dernière version analysée.
        </p>
        <template v-if="query">
          <p role="status">
            {{ statusLabels[query.status] }} · analyse {{ query.revision }} ·
            {{ date(query.created_at) }}
          </p>
          <p v-if="query.task_error" class="notice error">
            {{ query.task_error }}
          </p>
          <p v-if="query.obsolete" class="notice error" role="alert">
            Analyse obsolète : les entrées ont changé. Les résultats ci-dessous
            concernent exclusivement les entrées originales.
          </p>
          <details>
            <summary>Entrées figées de cette analyse</summary>
            <p>
              Point : {{ query.inputs.location.latitude }},
              {{ query.inputs.location.longitude }} · localisation r{{
                query.inputs.location.revision
              }}
              · profil r{{ query.inputs.profile_revision }}
            </p>
            <p>
              Interventions :
              {{
                query.inputs.profile.interventions
                  ?.map((code) => interventionLabels[code])
                  .join(", ") ||
                ("interventions" in query.inputs.profile
                  ? "Liste explicitement vide"
                  : "Non renseignées")
              }}
            </p>
            <p>
              {{ query.inputs.observations.length }} observation(s) humaine(s)
              retenue(s) · empreinte {{ query.input_sha256 }}
            </p>
          </details>
          <ul>
            <li v-for="(layer, name) in query.layers" :key="name">
              {{ name }} : {{ statusLabels[layer.status] }} ·
              {{ date(layer.retrieved_at)
              }}<span v-if="layer.error"> · {{ layer.error }}</span>
            </li>
          </ul>
        </template>
        <template v-if="result">
          <section v-if="result.dreal" aria-label="Zones humides DREAL">
            <h4>Zones humides DREAL Normandie</h4>
            <p>
              {{
                result.dreal.nature === "inventoried"
                  ? "Inventaire"
                  : "Prédisposition"
              }}
              : {{ statusLabels[result.dreal.status] }} ·
              {{ date(result.dreal.retrieved_at) }}
            </p>
            <p v-if="result.dreal.error" class="notice">
              {{ result.dreal.error }}
            </p>
            <p>
              Le point interrogé ne représente pas l’emprise des travaux. Une
              intersection justifie un examen, sans démontrer un impact. Une
              prédisposition n’est pas une zone humide confirmée ; un résultat
              vide ne prouve pas l’absence de zone humide.
            </p>
            <details>
              <summary>Provenance et objets retournés</summary>
              <p>
                Source :
                <a
                  v-if="result.dreal.source_url?.startsWith('https://')"
                  :href="result.dreal.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  >DREAL Normandie</a
                >
                <span v-else>{{ result.dreal.source_url }}</span>
              </p>
              <p v-if="result.dreal.projection">
                Projection : {{ result.dreal.projection }}
              </p>
              <p v-if="result.dreal.sha256">
                SHA-256 : {{ result.dreal.sha256 }}
              </p>
              <p v-if="result.dreal.parameters">
                Paramètres : {{ JSON.stringify(result.dreal.parameters) }}
              </p>
              <pre v-if="result.dreal.features?.length">{{
                JSON.stringify(result.dreal.features, null, 2)
              }}</pre>
            </details>
          </section>
          <h4>Ce que nous savons</h4>
          <ul>
            <li v-for="fact in result.facts" :key="fact.id">
              <strong>{{ kindLabels[fact.kind] }} :</strong> {{ fact.text }}
              <small>[{{ fact.id }}]</small>
            </li>
          </ul>
          <h4>Ce que votre projet doit examiner</h4>
          <ul>
            <li
              v-for="concern in result.project_concerns"
              :key="concern.project_action"
            >
              {{ concern.issue }}
            </li>
          </ul>
          <h3>4. Adapter mon projet</h3>
          <ProjectAlternatives
            :proposals="result.design_proposals"
            :facts="result.facts"
            :sources="result.sources"
            :obsolete="query?.obsolete"
          />
          <details class="complementary-checks">
            <summary>
              Vérifications complémentaires et propositions issues des preuves
            </summary>
            <p>
              Ces éléments complètent les alternatives de conception. Une
              proposition écologique qualifiée exige un appui documentaire
              examiné.
            </p>
            <div v-for="group in groups" :key="group.code" class="erc-group">
              <h4>{{ group.label }}</h4>
              <p
                v-if="
                  !result.actions.some(
                    (action) => action.category === group.code,
                  )
                "
              >
                Aucune proposition écologique qualifiée dans cette catégorie.
                Les alternatives de conception restent à étudier sous leurs
                conditions.
              </p>
              <article
                v-for="(action, index) in result.actions.filter(
                  (action) => action.category === group.code,
                )"
                :key="index"
                class="erc-action"
              >
                <h5>{{ action.issue }}</h5>
                <p class="eyebrow">
                  {{
                    action.evidence_status === "conditional_proposal"
                      ? "PROPOSITION CONDITIONNELLE"
                      : "VÉRIFICATION GÉNÉRALE"
                  }}
                </p>
                <p>{{ action.action }}</p>
                <p>{{ action.rationale }}</p>
                <details>
                  <summary>Justification et vérifications nécessaires</summary>
                  <p>
                    Déclencheurs :
                    {{ action.evidence_refs.join(", ") || "Projet à préciser" }}
                  </p>
                  <p>
                    Sources :
                    {{
                      action.source_refs.join(", ") ||
                      "Aucune source suffisante pour justifier une mesure"
                    }}
                  </p>
                  <p
                    v-for="item in [
                      ...action.preconditions,
                      ...action.missing_information,
                      ...action.limitations,
                    ]"
                    :key="item"
                  >
                    {{ item }}
                  </p>
                </details>
              </article>
            </div>
          </details>
          <p>
            <strong>Compenser : non évalué.</strong> Les impacts résiduels et
            leur éventuelle compensation nécessitent une étude adaptée.
          </p>
          <h3>5. Sources, incertitudes et limites</h3>
          <p v-if="query?.documentary_task">
            Complément documentaire facultatif :
            {{ documentaryLabel }}. Les résultats IGN restent indépendants.
          </p>
          <p v-if="result.documentary?.status === 'candidates_only'">
            Extraits complémentaires à examiner. Une correspondance lexicale ne
            justifie pas une mesure.
          </p>
          <ul>
            <li
              v-for="item in [...result.unknowns, ...result.limitations]"
              :key="item"
            >
              {{ item }}
            </li>
          </ul>
          <ul class="territorial-sources">
            <li v-for="source in result.sources" :key="source.id">
              [{{ source.id }}]
              <a
                v-if="source.url?.startsWith('https://')"
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
                >{{ source.title }}</a
              ><span v-else>{{ source.title }}</span
              ><span v-if="source.retrieved_at">
                · {{ date(source.retrieved_at) }}</span
              >
              <p v-if="source.text">{{ source.text }}</p>
              <p v-if="source.page">Page {{ source.page }}</p>
              <a
                v-if="source.original_url?.startsWith('/documents/')"
                :href="apiUrl(source.original_url)"
                target="_blank"
                rel="noopener noreferrer"
                >Lire le document source</a
              >
              <p v-if="source.relevance_reason">
                {{ source.relevance_reason }}
              </p>
              <p v-if="source.limitation">{{ source.limitation }}</p>
              <small v-if="source.sha256">SHA-256 : {{ source.sha256 }}</small>
            </li>
          </ul>
          <a
            v-if="query"
            class="button-link"
            :href="
              apiUrl(
                base + '/territorial-context/export?revision=' + query.revision,
              )
            "
            download
            >Exporter l’analyse et ses preuves (JSON)</a
          >
        </template>
        <p v-else>
          Les faits et vérifications apparaîtront après la consultation, sans
          attendre le rapport scientifique.
        </p>
      </template>
    </template>
  </section>
</template>
<style scoped>
.territorial-context {
  margin-block: 1.5rem;
}
.territorial-context h3 {
  margin-top: 1.8rem;
}
.territorial-context label.intervention-choice {
  flex-direction: row;
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0.5rem 1rem 0.5rem 0;
}
.territorial-context .intervention-choice input {
  width: 1rem;
  min-height: 1rem;
  padding: 0;
}
.erc-action {
  padding: 1rem;
  margin-block: 0.8rem;
  border-left: 3px solid #59826c;
  background: #f2f6f280;
  border-radius: 8px;
}
.erc-action h5 {
  font-size: 1rem;
  margin: 0;
}
.territorial-sources,
details {
  overflow-wrap: anywhere;
}
fieldset {
  border: 1px solid #b9ccbd;
  border-radius: 10px;
}
</style>
