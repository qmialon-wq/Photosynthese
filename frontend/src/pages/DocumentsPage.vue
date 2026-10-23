<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { api, apiUrl, date, message, post, useResource } from "../api";
import { documentStatus, externalUrl } from "../documents";
import type {
  Species,
  ScientificDocument,
  DocumentTask,
  DocumentPage,
} from "../documents";

const catalog = useResource<Species[]>(() => "/documents/species");
const species = ref("");
const selectedOnly = ref(false);
const offset = ref(0);
const limit = 12;
const documents = useResource<ScientificDocument[]>(() => {
  const query = new URLSearchParams({
    selected_only: String(selectedOnly.value),
    limit: String(limit),
    offset: String(offset.value),
  });
  if (species.value) query.set("species", species.value);
  return `/documents?${query}`;
});
watch([species, selectedOnly], () => {
  offset.value = 0;
});
const searchSpecies = ref("renards");
watch(species, (value) => {
  if (value) searchSpecies.value = value;
});
const topic = ref("ecology");
const territory = ref("");
const habitat = ref("");
const fulltext = ref(true);
const sources = ref(["openalex", "crossref", "europepmc"]);
const resultLimit = ref(5);
const showSearch = ref(false),
  showImport = ref(false);
const file = ref<File | null>(null),
  rights = ref(false),
  title = ref("");
const busy = ref(false),
  error = ref(""),
  success = ref("");
const tasks = useResource<DocumentTask[]>(
  () => "/documents/tasks?limit=10",
  2500,
);
const taskId = ref("");
const eventAfter = ref(0);
watch(taskId, () => {
  eventAfter.value = 0;
});
const task = useResource<DocumentTask>(
  () => (taskId.value ? `/documents/tasks/${taskId.value}` : null),
  2000,
);
const events = useResource<
  { id: number; stage: string; level: string; message: string }[]
>(
  () =>
    taskId.value
      ? `/documents/tasks/${taskId.value}/events?limit=100&after=${eventAfter.value}`
      : null,
  2500,
);
const detailId = ref(""),
  dialog = ref(false),
  pageOffset = ref(0);
const detail = useResource<ScientificDocument>(() =>
  detailId.value ? `/documents/${detailId.value}` : null,
);
const pages = useResource<DocumentPage[]>(() =>
  detailId.value
    ? `/documents/${detailId.value}/pages?limit=1&offset=${pageOffset.value}`
    : null,
);
const targetSpecies = ref("renards");
const chosenSpecies = computed(() =>
  catalog.data.value?.find((s) => s.name === species.value),
);
const summary = computed(() =>
  chosenSpecies.value
    ? `${chosenSpecies.value.documents_count} documents · ${chosenSpecies.value.selected_count} sources sélectionnées`
    : "Publications découvertes et sources sélectionnées pour les dix espèces.",
);
function available(doc: ScientificDocument, name: string) {
  return doc.species_links.some(
    (link) => link.species === name && link.available,
  );
}
async function refresh() {
  await Promise.all([
    documents.refresh(),
    catalog.refresh(),
    tasks.refresh(),
    detail.refresh(),
    pages.refresh(),
  ]);
}
watch(
  () => task.data.value?.status,
  (status) => {
    if (status && ["completed", "partial", "error"].includes(status))
      void refresh();
  },
);
async function action(run: () => Promise<unknown>, notice: string) {
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await run();
    success.value = notice;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function openDocument(doc: ScientificDocument) {
  detailId.value = doc.id;
  pageOffset.value = 0;
  targetSpecies.value =
    species.value || doc.species_links[0]?.species || "renards";
  dialog.value = true;
}
async function search() {
  await action(async () => {
    const selected = catalog.data.value?.find(
      (s) => s.name === searchSpecies.value,
    );
    if (!selected) throw new Error("Choisissez une espèce.");
    taskId.value = (
      await post<DocumentTask>("/documents/search", {
        species: [selected.scientific_name],
        topics: topic.value.trim() ? [topic.value.trim()] : [],
        habitats: habitat.value.trim() ? [habitat.value.trim()] : [],
        territories: territory.value.trim() ? [territory.value.trim()] : [],
        sources: sources.value,
        limit_per_source: resultLimit.value,
        download_fulltext: fulltext.value,
      })
    ).id;
    species.value = selected.name;
    selectedOnly.value = false;
    offset.value = 0;
    showSearch.value = false;
    await tasks.refresh();
  }, "Recherche lancée. Les documents apparaîtront après leur ingestion.");
}
function chooseFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}
async function upload() {
  await action(async () => {
    if (!file.value || !rights.value)
      throw new Error("Choisissez un fichier et confirmez les droits.");
    if (file.value.size > 32 * 1024 * 1024)
      throw new Error("La taille maximale est de 32 Mio.");
    const requestedSpecies = searchSpecies.value;
    const query = new URLSearchParams({
      filename: file.value.name,
      rights_confirmed: "true",
      species: requestedSpecies,
    });
    if (title.value.trim()) query.set("title", title.value.trim());
    taskId.value = (
      await api<DocumentTask>(`/documents/upload?${query}`, {
        method: "POST",
        body: file.value,
      })
    ).id;
    species.value = requestedSpecies;
    selectedOnly.value = false;
    offset.value = 0;
    showImport.value = false;
    rights.value = false;
    await tasks.refresh();
  }, "Fichier transmis. Son extraction se poursuit en arrière-plan.");
}
async function select(doc: ScientificDocument, name: string, enabled: boolean) {
  await action(
    async () => {
      await api(`/documents/${doc.id}/species/${name}`, {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      });
      await refresh();
    },
    enabled
      ? "Document validé et ajouté aux sources de cette espèce."
      : "Document retiré des sources de cette espèce.",
  );
}
async function fetchText(doc: ScientificDocument) {
  await action(async () => {
    taskId.value = (await post<DocumentTask>(`/documents/${doc.id}/fetch`)).id;
    await tasks.refresh();
  }, "Récupération du texte lancée, sous réserve de sa disponibilité et de sa licence.");
}
async function retry(job: DocumentTask) {
  await action(async () => {
    taskId.value = (
      await post<DocumentTask>(`/documents/tasks/${job.id}/retry`)
    ).id;
    await tasks.refresh();
  }, "Nouveau passage lancé.");
}
</script>

<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">CONNAISSANCE · SOURCES SCIENTIFIQUES</p>
      <h1>Documents scientifiques</h1>
      <p class="subtitle">
        Consultez et choisissez les publications qui alimenteront les futures
        recommandations.
      </p>
    </div>
    <div class="actions">
      <PButton
        label="Rechercher des publications"
        icon="pi pi-search"
        @click="
          showSearch = !showSearch;
          showImport = false;
        "
      />
      <PButton
        label="Importer un document"
        icon="pi pi-upload"
        severity="secondary"
        @click="
          showImport = !showImport;
          showSearch = false;
        "
      />
    </div>
  </div>
  <p class="notice">
    Le RAG n’est pas encore actif. Cette bibliothèque prépare ses sources :
    seuls les textes indexés et explicitement sélectionnés seront disponibles.
    L’ajout confirme leur pertinence et leur qualité ; le retrait reste
    réversible.
  </p>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <p v-if="success" class="notice" role="status">{{ success }}</p>
  <LoadState
    :error="catalog.error.value"
    :loading="catalog.loading.value && !catalog.data.value"
    @retry="catalog.refresh"
  >
    <section v-if="showSearch || showImport" class="panel">
      <h2>
        {{
          showSearch ? "Rechercher des publications" : "Importer un document"
        }}
      </h2>
      <form
        class="form-grid"
        @submit.prevent="showSearch ? search() : upload()"
      >
        <label
          >Espèce du document<select v-model="searchSpecies" required>
            <option
              v-for="item in catalog.data.value"
              :key="item.name"
              :value="item.name"
            >
              {{ item.display_name }} — {{ item.scientific_name }}
            </option>
          </select></label
        >
        <template v-if="showSearch">
          <div class="form-row">
            <label
              >Thématique<input
                v-model="topic"
                maxlength="200"
                placeholder="ecology, conservation…" /></label
            ><label
              >Habitat (facultatif)<input
                v-model="habitat"
                maxlength="200"
                placeholder="bocage, forest…" /></label
            ><label
              >Territoire (facultatif)<input
                v-model="territory"
                maxlength="200"
                placeholder="Normandy, France…"
            /></label>
          </div>
          <fieldset>
            <legend>Sources à interroger</legend>
            <label
              v-for="source in ['openalex', 'crossref', 'europepmc']"
              :key="source"
              class="check-line"
              ><input v-model="sources" type="checkbox" :value="source" />{{
                {
                  openalex: "OpenAlex",
                  crossref: "Crossref",
                  europepmc: "Europe PMC",
                }[source]
              }}</label
            >
          </fieldset>
          <label
            >Résultats maximum par source<input
              v-model.number="resultLimit"
              type="number"
              min="1"
              max="100"
              required
          /></label>
          <label class="check-line"
            ><input v-model="fulltext" type="checkbox" />Récupérer les textes
            intégraux autorisés</label
          >
          <p class="muted">
            Une recherche associe des candidats à cette espèce ; elle ne les
            ajoute pas automatiquement aux sources. Un filtre territorial strict
            peut écarter des études utiles.
          </p>
          <PButton
            type="submit"
            label="Lancer la recherche"
            :loading="busy"
            :disabled="!sources.length || !catalog.data.value?.length"
          />
        </template>
        <template v-else>
          <label
            >Fichier PDF, TXT ou Markdown (32 Mio maximum)<input
              type="file"
              accept=".pdf,.txt,.md"
              required
              @change="chooseFile"
          /></label>
          <label
            >Titre (facultatif)<input v-model="title" maxlength="1000"
          /></label>
          <label class="check-line"
            ><input v-model="rights" type="checkbox" required />Je dispose du
            droit de conserver et de traiter ce document.</label
          >
          <PButton
            type="submit"
            label="Importer et extraire le texte"
            :loading="busy"
            :disabled="!file || !rights"
          />
        </template>
      </form>
    </section>
  </LoadState>
  <section class="panel">
    <div class="section-head">
      <div>
        <h2>Bibliothèque par espèce</h2>
        <p class="muted">{{ summary }}</p>
      </div>
      <PButton
        label="Actualiser"
        icon="pi pi-refresh"
        severity="secondary"
        :disabled="documents.loading.value"
        @click="refresh"
      />
    </div>
    <div class="document-filters">
      <label
        >Filtrer par espèce<select v-model="species">
          <option value="">Toutes les espèces et documents non associés</option>
          <option
            v-for="item in catalog.data.value"
            :key="item.name"
            :value="item.name"
          >
            {{ item.display_name }} · {{ item.selected_count }} sources
          </option>
        </select></label
      >
      <label class="check-line"
        ><input v-model="selectedOnly" type="checkbox" />Sources sélectionnées
        uniquement</label
      >
    </div>
    <LoadState
      :error="documents.error.value"
      :loading="documents.loading.value && !documents.data.value"
      :empty="documents.data.value?.length === 0"
      empty-text="Aucun document pour ces filtres. Lancez une recherche ou importez un document."
      @retry="documents.refresh"
    >
      <div class="document-grid">
        <article
          v-for="doc in documents.data.value"
          :key="doc.id"
          class="document-card"
        >
          <div class="actions">
            <span class="document-tag">{{
              documentStatus[doc.status] || doc.status
            }}</span
            ><span
              v-if="doc.species_links.some((link) => link.available)"
              class="document-tag selected"
              >Source sélectionnée</span
            >
          </div>
          <h3>
            <button class="document-title" @click="openDocument(doc)">
              {{ doc.title }}
            </button>
          </h3>
          <p class="muted">
            {{ doc.authors.slice(0, 3).join(", ") || "Auteurs non renseignés"
            }}{{ doc.authors.length > 3 ? " et al." : "" }} ·
            {{ doc.published_date || "Date inconnue" }}
          </p>
          <p class="document-abstract">
            {{
              doc.abstract ||
              "Résumé non disponible. Consultez la notice et sa provenance."
            }}
          </p>
          <p class="muted">
            {{
              doc.species_links
                .map(
                  (link) =>
                    catalog.data.value?.find((s) => s.name === link.species)
                      ?.display_name || link.species,
                )
                .join(" · ") || "Aucune espèce associée"
            }}
          </p>
          <div class="actions">
            <PButton
              label="Consulter"
              severity="secondary"
              @click="openDocument(doc)"
            />
            <PButton
              v-if="species && available(doc, species)"
              label="Retirer des sources"
              severity="secondary"
              :disabled="busy"
              @click="select(doc, species, false)"
            />
            <PButton
              v-else-if="species && doc.status === 'indexed'"
              label="Valider et ajouter"
              :disabled="busy"
              @click="select(doc, species, true)"
            />
            <PButton
              v-else-if="
                ['discovered', 'inaccessible', 'imported'].includes(doc.status)
              "
              label="Récupérer le texte"
              severity="secondary"
              :disabled="busy"
              @click="fetchText(doc)"
            />
          </div>
        </article>
      </div>
    </LoadState>
    <div class="actions pagination">
      <PButton
        label="Page précédente"
        severity="secondary"
        :disabled="offset === 0 || documents.loading.value"
        @click="offset -= limit"
      /><span>Page {{ Math.floor(offset / limit) + 1 }}</span
      ><PButton
        label="Page suivante"
        severity="secondary"
        :disabled="
          documents.data.value?.length !== limit || documents.loading.value
        "
        @click="offset += limit"
      />
    </div>
  </section>
  <section class="panel">
    <h2>Recherches et imports récents</h2>
    <LoadState
      :error="tasks.error.value"
      :loading="tasks.loading.value && !tasks.data.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucune tâche documentaire lancée."
      @retry="tasks.refresh"
    >
      <ul class="document-tasks">
        <li v-for="job in tasks.data.value" :key="job.id">
          <div>
            <strong>{{
              {
                search: "Recherche",
                import: "Import",
                fetch: "Récupération",
                index: "Indexation",
              }[job.kind] || job.kind
            }}</strong>
            · {{ documentStatus[job.status] || job.status
            }}<small
              >{{ date(job.created_at)
              }}<template v-if="job.result?.observed != null">
                · {{ job.result.observed }} notices ·
                {{ job.result.errors || 0 }} erreurs ·
                {{ job.result.inaccessible || 0 }} textes
                inaccessibles</template
              ></small
            >
            <p v-if="job.error" class="notice error">{{ job.error }}</p>
          </div>
          <div class="actions">
            <PButton
              label="Voir le journal"
              severity="secondary"
              @click="taskId = job.id"
            /><PButton
              v-if="['error', 'partial'].includes(job.status)"
              label="Relancer"
              severity="secondary"
              :disabled="busy"
              @click="retry(job)"
            />
          </div>
        </li>
      </ul>
    </LoadState>
    <div v-if="taskId" class="document-log">
      <h3>Journal de la tâche</h3>
      <p v-if="task.data.value" role="status">
        {{ documentStatus[task.data.value.status] || task.data.value.status }}
      </p>
      <LoadState
        :error="task.error.value || events.error.value"
        :loading="events.loading.value && !events.data.value"
        @retry="
          task.refresh();
          events.refresh();
        "
        ><ol>
          <li v-for="entry in events.data.value" :key="entry.id">
            {{ entry.stage }} · {{ entry.message }}
          </li>
        </ol></LoadState
      >
      <div class="actions">
        <PButton
          label="Début du journal"
          severity="secondary"
          :disabled="eventAfter === 0 || events.loading.value"
          @click="eventAfter = 0"
        />
        <PButton
          label="Suite du journal"
          severity="secondary"
          :disabled="events.data.value?.length !== 100 || events.loading.value"
          @click="eventAfter = events.data.value!.at(-1)!.id"
        />
      </div>
    </div>
  </section>
  <PDialog
    v-model:visible="dialog"
    modal
    header="Document scientifique"
    :style="{ width: '900px', maxWidth: '95vw' }"
  >
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>
    <p v-if="success" class="notice" role="status">{{ success }}</p>
    <LoadState
      :error="detail.error.value"
      :loading="detail.loading.value"
      @retry="detail.refresh"
      ><template v-if="detail.data.value">
        <h2>{{ detail.data.value.title }}</h2>
        <p>{{ detail.data.value.authors.join(", ") }}</p>
        <p class="muted">
          {{ detail.data.value.published_date || "Date inconnue" }} ·
          {{ detail.data.value.language || "Langue non déterminée" }} ·
          {{ documentStatus[detail.data.value.status] }}
        </p>
        <div class="actions">
          <a
            v-if="externalUrl(detail.data.value.url)"
            :href="externalUrl(detail.data.value.url)"
            target="_blank"
            rel="noopener noreferrer"
            >Notice chez la source <i class="pi pi-external-link" /></a
          ><a
            v-if="detail.data.value.doi"
            :href="
              'https://doi.org/' + encodeURIComponent(detail.data.value.doi)
            "
            target="_blank"
            rel="noopener noreferrer"
            >DOI : {{ detail.data.value.doi }}</a
          >
        </div>
        <p>{{ detail.data.value.abstract || "Résumé non disponible." }}</p>
        <div class="document-selection">
          <label
            >Espèce concernée<select v-model="targetSpecies">
              <option
                v-for="item in catalog.data.value"
                :key="item.name"
                :value="item.name"
              >
                {{ item.display_name }}
              </option>
            </select></label
          >
          <PButton
            v-if="available(detail.data.value, targetSpecies)"
            label="Retirer des sources"
            severity="secondary"
            :disabled="busy"
            @click="select(detail.data.value!, targetSpecies, false)"
          />
          <PButton
            v-else
            label="Valider et ajouter aux sources"
            :disabled="busy || detail.data.value.status !== 'indexed'"
            @click="select(detail.data.value!, targetSpecies, true)"
          />
        </div>
        <p class="muted">
          L’ajout confirme que vous avez vérifié la pertinence et la qualité du
          texte pour cette espèce. Aucun commentaire ni nom d’utilisateur à
          saisir.
        </p>
        <p v-if="detail.data.value.status !== 'indexed'" class="notice">
          Ce document ne peut pas être ajouté tant qu’un texte intégral
          exploitable n’est pas indexé.
        </p>
        <PButton
          v-if="!['indexed', 'rejected'].includes(detail.data.value.status)"
          label="Récupérer le texte"
          severity="secondary"
          :disabled="busy"
          @click="fetchText(detail.data.value!)"
        />
        <h3>Originaux et licences</h3>
        <ul>
          <li v-for="asset in detail.data.value.assets" :key="asset.id">
            <a
              :href="apiUrl(`/documents/${detailId}/assets/${asset.id}`)"
              download
              >Télécharger le {{ asset.format.toUpperCase() }}</a
            ><template v-if="asset.format === 'pdf'">
              ·
              <a
                :href="
                  apiUrl(
                    `/documents/${detailId}/assets/${asset.id}?inline=true`,
                  )
                "
                target="_blank"
                rel="noopener noreferrer"
                >Ouvrir le PDF</a
              ></template
            >
            · {{ asset.license
            }}<small class="document-hash">SHA-256 : {{ asset.sha256 }}</small>
          </li>
        </ul>
        <p v-if="!detail.data.value.assets?.length" class="muted">
          Aucun texte intégral conservé. L’accès dépend de la licence et de la
          disponibilité de la publication.
        </p>
        <h3>Texte extrait</h3>
        <LoadState
          :error="pages.error.value"
          :loading="pages.loading.value"
          :empty="pages.data.value?.length === 0"
          empty-text="Aucune page de texte disponible."
          @retry="pages.refresh"
          ><div
            v-for="page in pages.data.value"
            :key="page.asset_id + ':' + page.page_number"
          >
            <p class="muted">
              Page {{ page.page_number }} · {{ page.language
              }}<template
                v-if="
                  detail.data.value.assets?.find((a) => a.id === page.asset_id)
                    ?.format !== 'pdf'
                "
              >
                · page logique, sans pagination PDF</template
              >
            </p>
            <pre class="document-text">{{ page.clean_text }}</pre>
            <details v-if="page.references_data.length">
              <summary>Références de cette page</summary>
              <ul>
                <li v-for="(reference, i) in page.references_data" :key="i">
                  {{ reference.text || reference.url }}
                </li>
              </ul>
            </details>
          </div></LoadState
        >
        <div class="actions pagination">
          <PButton
            label="Texte précédent"
            severity="secondary"
            :disabled="pageOffset === 0 || pages.loading.value"
            @click="pageOffset--"
          /><PButton
            label="Texte suivant"
            severity="secondary"
            :disabled="!pages.data.value?.length || pages.loading.value"
            @click="pageOffset++"
          />
        </div>
        <details>
          <summary>Provenance et historique des sélections</summary>
          <ul>
            <li
              v-for="(source, index) in detail.data.value.provenance"
              :key="index"
            >
              {{ source.source }} · {{ date(source.observed_at) }}
            </li>
            <li
              v-for="(entry, index) in detail.data.value.selection_history"
              :key="'h' + index"
            >
              {{ entry.enabled ? "Ajout" : "Retrait" }} · {{ entry.species }} ·
              {{ date(entry.created_at) }} · {{ entry.actor }}
            </li>
          </ul>
        </details>
      </template></LoadState
    >
  </PDialog>
</template>
