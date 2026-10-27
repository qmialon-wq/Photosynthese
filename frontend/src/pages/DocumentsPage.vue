<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { apiUrl, api, date, message, post, useResource } from "../api";
import { auth } from "../auth-state";
const canManage = computed(() => auth.user?.role === "admin");
import { documentStatus } from "../documents";
import type {
  Species,
  ScientificDocument,
  DocumentTask,
  DocumentPage,
} from "../documents";

const catalog = useResource<Species[]>(() => "/documents/species", 5000);
const species = ref("renards");
const offset = ref(0),
  limit = 12;
const picked = ref<string[]>([]),
  targets = ref<string[]>(["renards"]);
const chooseSpecies = ref(false),
  importOpen = ref(false);
const busy = ref(false),
  error = ref(""),
  notice = ref("");
const documents = useResource<ScientificDocument[]>(
  () =>
    `/documents?stored_only=true&species=${encodeURIComponent(species.value)}&limit=${limit}&offset=${offset.value}`,
  5000,
);
watch(species, () => {
  offset.value = 0;
  picked.value = [];
});
watch(offset, () => {
  picked.value = [];
});
watch(
  () => documents.data.value,
  (rows) => {
    picked.value = picked.value.filter((id) =>
      rows?.some((row) => row.id === id),
    );
  },
);
const allPicked = computed(
  () =>
    !!documents.data.value?.length &&
    documents.data.value.every((d) => picked.value.includes(d.id)),
);
const tasks = useResource<DocumentTask[]>(
  () => "/documents/tasks?limit=12",
  3000,
);
const running = computed(
  () =>
    tasks.data.value?.filter((t) => ["queued", "running"].includes(t.status))
      .length ?? 0,
);
const file = ref<File | null>(null),
  rights = ref(false);
const detailId = ref(""),
  dialog = ref(false),
  original = ref(false),
  pageOffset = ref(0);
const detail = useResource<ScientificDocument>(
  () => (detailId.value ? `/documents/${detailId.value}` : null),
  4000,
);
const pages = useResource<DocumentPage[]>(
  () =>
    detailId.value
      ? `/documents/${detailId.value}/pages?limit=1&offset=${pageOffset.value}`
      : null,
  5000,
);

function french(doc: ScientificDocument) {
  const translation = doc.metadata?.translation_fr;
  return translation?.source_title === doc.title ? translation : undefined;
}
function title(doc: ScientificDocument) {
  return french(doc)?.title || doc.title;
}
function translationLabel(doc: ScientificDocument) {
  if (doc.status !== "indexed")
    return "Original disponible · texte non extrait";
  const state = doc.metadata?.translation_fr?.status;
  if (doc.language === "fr" || state === "original_fr")
    return "Document en français";
  if (state === "completed") return "Traduit en français";
  if (state === "error") return "Traduction à relancer";
  if (state === "unsupported")
    return "Traduction indisponible pour cette langue";
  return "Traduction en préparation";
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
async function action(run: () => Promise<unknown>, success: string) {
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await run();
    notice.value = success;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function collect(all: boolean) {
  await action(async () => {
    await post("/documents/collect", { species: all ? [] : targets.value });
    chooseSpecies.value = false;
    await tasks.refresh();
  }, "Récupération lancée. Les documents disponibles seront téléchargés puis traduits automatiquement.");
}
async function remove() {
  await action(async () => {
    await post("/documents/remove", {
      species: species.value,
      documents: picked.value,
    });
    picked.value = [];
    await refresh();
  }, "Documents retirés du corpus de cette espèce.");
}
function selectAll(event: Event) {
  picked.value = (event.target as HTMLInputElement).checked
    ? (documents.data.value ?? []).map((d) => d.id)
    : [];
}
function open(doc: ScientificDocument) {
  detailId.value = doc.id;
  pageOffset.value = 0;
  original.value = false;
  dialog.value = true;
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
    const query = new URLSearchParams({
      filename: file.value.name,
      species: species.value,
      rights_confirmed: "true",
    });
    await api(`/documents/upload?${query}`, {
      method: "POST",
      body: file.value,
    });
    importOpen.value = false;
    rights.value = false;
    await tasks.refresh();
  }, "Import lancé. Le document sera traduit automatiquement après extraction.");
}
async function translate(doc: ScientificDocument) {
  await action(async () => {
    await post(`/documents/${doc.id}/translate`);
    await refresh();
  }, "Traduction lancée.");
}
</script>

<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">CONNAISSANCE · CORPUS DOCUMENTAIRE</p>
      <h1>Documents scientifiques</h1>
      <p class="subtitle">
        Objectif : 100 articles par espèce sur la faune et les activités
        humaines, avec des recherches dédiées aux milieux urbains et agricoles.
        Le nombre disponible dépend des publications accessibles.
      </p>
    </div>
    <div v-if="canManage" class="actions">
      <PButton
        label="Récupérer pour toutes les espèces"
        icon="pi pi-download"
        :loading="busy"
        @click="collect(true)"
      /><PButton
        label="Choisir les espèces"
        severity="secondary"
        :disabled="busy"
        @click="
          chooseSpecies = !chooseSpecies;
          importOpen = false;
        "
      />
    </div>
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <p v-if="notice" class="notice" role="status">{{ notice }}</p>
  <section v-if="canManage && chooseSpecies" class="panel">
    <h2>Pour quelles espèces ?</h2>
    <LoadState
      :error="catalog.error.value"
      :loading="catalog.loading.value && !catalog.data.value"
      @retry="catalog.refresh"
    >
      <form @submit.prevent="collect(false)">
        <fieldset class="species-choices">
          <legend>Espèces à rechercher</legend>
          <label
            v-for="item in catalog.data.value"
            :key="item.name"
            class="check-line"
            ><input v-model="targets" type="checkbox" :value="item.name" />{{
              item.display_name
            }}</label
          >
        </fieldset>
        <PButton
          type="submit"
          label="Récupérer les documents des espèces choisies"
          :loading="busy"
          :disabled="!targets.length"
        />
      </form>
    </LoadState>
  </section>
  <section class="panel">
    <div class="section-head">
      <div>
        <h2>Mon corpus</h2>
        <p class="muted">
          Seuls les documents téléchargés apparaissent ici. Les originaux
          restent accessibles.
        </p>
      </div>
      <PButton
        v-if="canManage"
        label="Importer un document"
        icon="pi pi-upload"
        severity="secondary"
        @click="
          importOpen = !importOpen;
          chooseSpecies = false;
        "
      />
    </div>
    <LoadState
      :error="catalog.error.value"
      :loading="catalog.loading.value && !catalog.data.value"
      @retry="catalog.refresh"
      ><label class="document-species-filter"
        >Espèce<select v-model="species" aria-label="Espèce">
          <option
            v-for="item in catalog.data.value"
            :key="item.name"
            :value="item.name"
          >
            {{ item.display_name }} · {{ item.documents_count }} documents
          </option>
        </select></label
      ></LoadState
    >
    <form
      v-if="canManage && importOpen"
      class="form-grid document-search-form"
      @submit.prevent="upload"
    >
      <label
        >Fichier PDF, TXT ou Markdown (32 Mio maximum)<input
          type="file"
          accept=".pdf,.txt,.md"
          required
          @change="chooseFile" /></label
      ><label class="check-line"
        ><input v-model="rights" type="checkbox" required />Je dispose du droit
        de conserver et traiter ce document.</label
      ><PButton
        type="submit"
        label="Importer le document"
        :loading="busy"
        :disabled="!file || !rights"
      />
    </form>
    <div v-if="canManage" class="bulk-toolbar">
      <label class="check-line"
        ><input
          type="checkbox"
          :checked="allPicked"
          :disabled="!documents.data.value?.length"
          @change="selectAll"
        />Tout sélectionner sur cette page</label
      ><span aria-live="polite">{{ picked.length }} sélectionné(s)</span
      ><PButton
        label="Retirer du corpus"
        icon="pi pi-trash"
        severity="danger"
        :disabled="busy || !picked.length"
        @click="remove"
      />
    </div>
    <LoadState
      :error="documents.error.value"
      :loading="documents.loading.value && !documents.data.value"
      :empty="documents.data.value?.length === 0"
      empty-text="Aucun document téléchargé pour cette espèce. Lancez une récupération ou importez un fichier."
      @retry="documents.refresh"
    >
      <div class="document-grid">
        <article
          :data-document-id="doc.id"
          v-for="doc in documents.data.value"
          :key="doc.id"
          class="document-card"
        >
          <label v-if="canManage" class="check-line"
            ><input
              v-model="picked"
              type="checkbox"
              :value="doc.id"
              :aria-label="'Sélectionner ' + title(doc)"
            />Sélectionner</label
          >
          <h3>
            <button class="document-title" @click="open(doc)">
              {{ title(doc) }}
            </button>
          </h3>
          <p class="muted">
            {{ doc.authors.slice(0, 2).join(", ") || "Auteur non renseigné" }} ·
            {{ doc.published_date || "Date non renseignée" }}
          </p>
          <p class="document-abstract">
            {{
              french(doc)?.abstract ||
              "Ouvrez le document pour consulter son contenu."
            }}
          </p>
          <p class="muted">{{ translationLabel(doc) }}</p>
          <PButton
            label="Lire le document"
            icon="pi pi-book"
            severity="secondary"
            @click="open(doc)"
          />
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
    <div class="section-head">
      <h2>Avancement</h2>
      <span v-if="running" role="status">Traitement en cours</span>
    </div>
    <LoadState
      :error="tasks.error.value"
      :loading="tasks.loading.value && !tasks.data.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucune récupération en cours."
      @retry="tasks.refresh"
      ><ul class="document-tasks">
        <li v-for="job in tasks.data.value" :key="job.id">
          <div>
            <strong>{{
              job.kind === "translate"
                ? "Traduction en français"
                : job.kind === "import"
                  ? "Import du document"
                  : "Récupération des documents"
            }}</strong>
            · {{ documentStatus[job.status] || job.status
            }}<small
              >{{ date(job.created_at)
              }}<template v-if="job.request.collection_species">
                ·
                {{
                  catalog.data.value?.find(
                    (s) => s.name === job.request.collection_species,
                  )?.display_name
                }}</template
              ><template v-if="job.result?.downloaded != null">
                · {{ job.result.downloaded }} document(s)
                <template v-if="job.result.corpus_count != null">
                  · Corpus : {{ job.result.corpus_count }} /
                  {{ job.result.target }}
                  <template v-if="job.result.target_reached === false">
                    · Objectif non atteint avec les textes accessibles
                  </template>
                </template>
                téléchargé(s)</template
              ></small
            >
            <p v-if="job.error" class="notice error">
              Le traitement a rencontré un problème. Vous pouvez relancer la
              récupération ou la traduction.
            </p>
          </div>
        </li>
      </ul></LoadState
    >
  </section>
  <PDialog
    v-model:visible="dialog"
    modal
    header="Lire le document"
    :style="{ width: '950px', maxWidth: '95vw' }"
  >
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>
    <LoadState
      :error="detail.error.value"
      :loading="detail.loading.value && !detail.data.value"
      @retry="detail.refresh"
      ><template v-if="detail.data.value">
        <h2>
          {{ original ? detail.data.value.title : title(detail.data.value) }}
        </h2>
        <div class="actions">
          <PButton
            label="Français"
            :severity="original ? 'secondary' : 'primary'"
            :aria-pressed="!original"
            @click="original = false"
          /><PButton
            label="Original"
            :severity="original ? 'primary' : 'secondary'"
            :aria-pressed="original"
            @click="original = true"
          /><a
            v-if="
              detail.data.value.metadata?.translation_fr?.status === 'completed'
            "
            :href="apiUrl(`/documents/${detailId}/translation`)"
            download
            >Télécharger la traduction</a
          >
        </div>
        <p class="muted">
          {{
            original
              ? "Texte original"
              : detail.data.value.language === "fr"
                ? "Document rédigé en français"
                : "Traduction automatique, original conservé pour vérification."
          }}
        </p>
        <LoadState
          :error="pages.error.value"
          :loading="pages.loading.value && !pages.data.value"
          :empty="pages.data.value?.length === 0"
          empty-text="Le texte n’a pas pu être extrait. Vous pouvez ouvrir le fichier original ci-dessous."
          @retry="pages.refresh"
          ><div
            v-for="page in pages.data.value"
            :key="page.asset_id + ':' + page.page_number"
          >
            <p class="muted">
              Page {{ page.page_number
              }}<template
                v-if="
                  detail.data.value.assets?.find((a) => a.id === page.asset_id)
                    ?.format !== 'pdf'
                "
              >
                · page logique du document</template
              >
            </p>
            <pre
              v-if="
                original ||
                detail.data.value.language === 'fr' ||
                page.translated_text
              "
              class="document-text"
              >{{
                original || detail.data.value.language === "fr"
                  ? page.clean_text
                  : page.translated_text
              }}</pre
            >
            <p v-else class="notice">
              {{ translationLabel(detail.data.value)
              }}<template
                v-if="
                  detail.data.value.metadata?.translation_fr?.pages_done != null
                "
              >
                · {{ detail.data.value.metadata.translation_fr.pages_done }}/{{
                  detail.data.value.metadata.translation_fr.pages_total
                }}
                pages</template
              >
            </p>
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
          /><PButton
            v-if="
              canManage &&
              (['error', 'unsupported'].includes(
                detail.data.value.metadata?.translation_fr?.status || '',
              ) ||
                !detail.data.value.metadata?.translation_fr)
            "
            label="Relancer la traduction"
            severity="secondary"
            :disabled="busy || detail.data.value.language !== 'en'"
            @click="translate(detail.data.value!)"
          />
        </div>
        <details>
          <summary>Originaux et sources</summary>
          <p>
            {{ detail.data.value.authors.join(", ") }} ·
            {{ detail.data.value.published_date }}
          </p>
          <ul>
            <li v-for="asset in detail.data.value.assets" :key="asset.id">
              <a
                :href="
                  apiUrl(
                    `/documents/${detailId}/assets/${asset.id}?inline=true`,
                  )
                "
                target="_blank"
                rel="noopener noreferrer"
                >Ouvrir l’original ({{ asset.format.toUpperCase() }})</a
              >
              · {{ asset.license }}
            </li>
          </ul>
          <p v-if="detail.data.value.doi">DOI : {{ detail.data.value.doi }}</p>
        </details>
      </template></LoadState
    >
  </PDialog>
</template>
