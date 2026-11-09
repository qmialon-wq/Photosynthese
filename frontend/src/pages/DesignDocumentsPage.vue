<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import FilterSelect from "../components/symbiose/FilterSelect.vue";
import Pagination from "../components/symbiose/Pagination.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import DocumentList from "../components/symbiose/DocumentList.vue";
import DocumentEmptyState from "../components/symbiose/DocumentEmptyState.vue";
import RetrievalProgress from "../components/symbiose/RetrievalProgress.vue";
import {
  corpusSpecies,
  corpusSpeciesLabel,
  currentDocumentSelection,
  demoScientificDocuments,
  documentPageSize,
  documentSpeciesOptions,
  documentsForSpecies,
  fictitiousDocumentDate,
  importedDocumentKind,
  removePreviewDocuments,
  retrievalExampleDocuments,
  retrievalQueueDelay,
  retrievalSteps,
  retrievalTickDuration,
  type DemoScientificDocument,
  type DemoRetrievalTask,
} from "../data/document-preview";
import "../styles/videotheque.css";
import "../styles/scientific-documents.css";

const documents = ref(
  demoScientificDocuments.map((document) => ({ ...document })),
);
const species = ref("renard"),
  page = ref(1),
  selected = ref(new Set<string>());
const speciesOptions = computed(() => documentSpeciesOptions(documents.value));
const filtered = computed(() =>
  documentsForSpecies(documents.value, species.value),
);
const visible = computed(() =>
  filtered.value.slice(
    (page.value - 1) * documentPageSize,
    page.value * documentPageSize,
  ),
);
const selection = computed(() =>
  currentDocumentSelection(visible.value, selected.value),
);
const allSelected = computed(
  () =>
    !!visible.value.length && selection.value.length === visible.value.length,
);
const partlySelected = computed(
  () => !!selection.value.length && !allSelected.value,
);
const feedback = ref(""),
  importError = ref("");
type DialogKind = "all" | "species" | "import" | "remove" | "preview";
const dialog = ref<DialogKind | null>(null),
  currentDocument = ref<DemoScientificDocument | null>(null);
const chosenSpecies = ref(corpusSpecies.map((option) => option.value)),
  draftSpecies = ref<string[]>([]);
const fileInput = ref<HTMLInputElement>(),
  importSpecies = ref("renard");
const pendingImport = ref<{
  filename: string;
  kind: DemoScientificDocument["kind"];
  species: string;
} | null>(null);
const task = ref<DemoRetrievalTask | null>(null);
const busy = computed(() => !!task.value && task.value.status !== "completed");
const dialogTitle = computed(
  () =>
    ({
      all: "Simuler une récupération",
      species: "Choisir les espèces",
      import: "Importer un document",
      remove: "Retirer du corpus",
      preview: "Consulter un document de démonstration",
    })[dialog.value || "preview"],
);
let queueTimer: ReturnType<typeof setTimeout> | undefined,
  progressTimer: ReturnType<typeof setInterval> | undefined,
  runNumber = 0,
  importNumber = 0;
function stopTimers() {
  if (queueTimer) clearTimeout(queueTimer);
  if (progressTimer) clearInterval(progressTimer);
  queueTimer = undefined;
  progressTimer = undefined;
}
function closeDialog() {
  dialog.value = null;
  pendingImport.value = null;
  currentDocument.value = null;
}
watch(species, () => {
  page.value = 1;
  selected.value.clear();
  feedback.value = "";
  importError.value = "";
});
watch(page, () => selected.value.clear());
watch(
  () => filtered.value.length,
  () => {
    page.value = Math.min(
      page.value,
      Math.max(1, Math.ceil(filtered.value.length / documentPageSize)),
    );
  },
);
function toggle(id: string) {
  if (!visible.value.some((document) => document.id === id)) return;
  if (selected.value.has(id)) selected.value.delete(id);
  else selected.value.add(id);
}
function togglePage() {
  selected.value = allSelected.value
    ? new Set()
    : new Set(visible.value.map((document) => document.id));
}
function chooseSpecies() {
  draftSpecies.value = [...chosenSpecies.value];
  dialog.value = "species";
}
function startRetrieval(targets: string[]) {
  const ids = corpusSpecies
    .filter((option) => targets.includes(option.value))
    .map((option) => option.value);
  if (!ids.length || busy.value) return;
  closeDialog();
  stopTimers();
  chosenSpecies.value = [...ids];
  feedback.value = "";
  task.value = { species: ids, status: "queued", progress: 0 };
  const run = ++runNumber;
  queueTimer = setTimeout(() => {
    queueTimer = undefined;
    if (!task.value) return;
    task.value.status = "running";
    let step = 0;
    progressTimer = setInterval(() => {
      if (!task.value) return;
      task.value.progress = retrievalSteps[step++];
      if (task.value.progress === 100) {
        stopTimers();
        task.value.status = "completed";
        documents.value = [
          ...documents.value,
          ...retrievalExampleDocuments(ids, run),
        ];
        feedback.value = `Démonstration : ${ids.length} exemple${ids.length > 1 ? "s" : ""} fictif${ids.length > 1 ? "s" : ""} ajouté${ids.length > 1 ? "s" : ""}. Aucun article n’a été recherché ou téléchargé.`;
      }
    }, retrievalTickDuration);
  }, retrievalQueueDelay);
}
function openFilePicker() {
  importError.value = "";
  importSpecies.value = species.value;
  fileInput.value?.click();
}
function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement,
    file = input.files?.[0];
  if (!file) return;
  const kind = importedDocumentKind(file.name);
  if (!kind) {
    importError.value =
      "Choisissez un fichier PDF, DOCX ou TXT. Aucun fichier n’a été lu ou envoyé.";
    input.value = "";
    return;
  }
  importError.value = "";
  pendingImport.value = {
    filename: file.name,
    kind,
    species: importSpecies.value,
  };
  input.value = "";
  dialog.value = "import";
}
function confirmImport() {
  if (!pendingImport.value) return;
  const pending = pendingImport.value;
  species.value = pending.species;
  page.value = 1;
  selected.value.clear();
  documents.value = [
    {
      id: `import-${++importNumber}`,
      species: pending.species,
      title: `Import simulé — ${pending.filename}`,
      filename: pending.filename,
      kind: pending.kind,
      date: fictitiousDocumentDate,
      origin: "import",
    },
    ...documents.value,
  ];
  feedback.value = `Entrée fictive ajoutée pour « ${pending.filename} ». Aucun contenu de fichier n’a été lu, envoyé ou enregistré.`;
  closeDialog();
}
function removeSelection() {
  if (!selection.value.length) {
    closeDialog();
    return;
  }
  const count = selection.value.length;
  documents.value = removePreviewDocuments(
    documents.value,
    visible.value,
    selected.value,
  );
  selected.value.clear();
  closeDialog();
  feedback.value = `${count} entrée${count > 1 ? "s" : ""} fictive${count > 1 ? "s" : ""} retirée${count > 1 ? "s" : ""} du corpus local. Aucun fichier réel n’a été supprimé.`;
}
function preview(document: DemoScientificDocument) {
  currentDocument.value = document;
  dialog.value = "preview";
}
onBeforeUnmount(stopTimers);
</script>
<template>
  <GlassPanel
    depth="page"
    class="sv-page sd-page"
    topography
    aria-labelledby="sd-title"
  >
    <header class="sv-header sd-header">
      <div class="sv-heading">
        <span class="sv-heading-icon"
          ><SymIcon name="layers" :size="42"
        /></span>
        <div>
          <h1 id="sd-title">Documents scientifiques</h1>
          <p>
            Objectif : 100 articles par espèce sur la faune et les activités
            humaines, avec des recherches dédiées aux milieux urbains et
            agricoles. Le nombre disponible dépend des publications accessibles.
          </p>
        </div>
      </div>
      <div class="sd-header-actions">
        <button class="sym-button" :disabled="busy" @click="dialog = 'all'">
          <SymIcon name="download" :size="23" />Récupérer pour toutes les
          espèces</button
        ><button
          class="sv-button-quiet"
          :disabled="busy"
          @click="chooseSpecies"
        >
          Choisir les espèces
        </button>
      </div>
    </header>
    <GlassPanel class="sd-corpus" aria-labelledby="sd-corpus-title"
      ><header class="sd-corpus-header">
        <div class="sd-corpus-heading">
          <span class="sv-heading-icon sd-section-icon"
            ><SymIcon name="folder" :size="33"
          /></span>
          <div>
            <h2 id="sd-corpus-title" class="sd-section-title">Mon corpus</h2>
            <p>
              Seuls les documents téléchargés apparaissent ici. Les originaux
              restent accessibles.
            </p>
          </div>
        </div>
        <button class="sv-button-quiet sd-import" @click="openFilePicker">
          <SymIcon name="upload" :size="23" />Importer un document</button
        ><input
          ref="fileInput"
          class="sym-sr-only"
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          aria-label="Choisir un fichier à importer"
          tabindex="-1"
          @change="chooseFile"
        />
      </header>
      <div class="sd-species-field">
        <span aria-hidden="true">Espèce</span
        ><FilterSelect
          v-model="species"
          label="Espèce du corpus"
          :options="speciesOptions"
        />
      </div>
      <GlassPanel class="sd-selection-bar"
        ><label class="sd-select-page"
          ><input
            type="checkbox"
            :checked="allSelected"
            :indeterminate="partlySelected"
            :disabled="!visible.length"
            @change="togglePage"
          />Tout sélectionner sur cette page</label
        ><span class="sd-selection-count" role="status"
          >{{ selection.length }} sélectionné(s)</span
        ><button
          class="sv-button-quiet sym-button-danger sd-remove"
          :disabled="!selection.length"
          @click="dialog = 'remove'"
        >
          <SymIcon name="trash" :size="20" />Retirer du corpus
        </button></GlassPanel
      >
      <DocumentList
        v-if="visible.length"
        :documents="visible"
        :selected="selected"
        @toggle="toggle"
        @preview="preview"
      /><DocumentEmptyState
        v-else
        message="Aucun document téléchargé pour cette espèce. Lancez une récupération ou importez un fichier."
      />
      <Pagination
        class="sd-pagination"
        variant="simple"
        :page="page"
        :total="filtered.length"
        :page-size="documentPageSize"
        item-label="document"
        navigation-label="Pagination du corpus"
        @change="page = $event"
      />
    </GlassPanel>
    <p v-if="feedback" class="sd-feedback" role="status">{{ feedback }}</p>
    <p v-if="importError" class="sd-feedback sd-error" role="alert">
      {{ importError }}
    </p>
    <RetrievalProgress :task="task" />
    <DemoDialog :open="!!dialog" :title="dialogTitle" @close="closeDialog"
      ><template v-if="dialog === 'all'"
        ><p>
          Cette démonstration simule une récupération pour les
          {{ corpusSpecies.length }} espèces :
          {{ corpusSpecies.map((option) => option.label).join(", ") }}.
        </p>
        <p>
          Aucune recherche scientifique, collecte ou téléchargement réel ne sera
          effectué. Seuls des exemples fictifs seront ajoutés au corpus local.
        </p>
        <div class="sd-dialog-actions">
          <button class="sv-button-quiet" @click="closeDialog">Annuler</button
          ><button
            class="sym-button"
            @click="startRetrieval(corpusSpecies.map((option) => option.value))"
          >
            Confirmer la simulation
          </button>
        </div></template
      >
      <template v-else-if="dialog === 'species'"
        ><p>
          Choisissez les espèces pour une récupération simulée. Confirmer lance
          uniquement la démonstration locale, sans recherche ni téléchargement
          réel.
        </p>
        <div class="sd-species-choices">
          <label v-for="option in corpusSpecies" :key="option.value"
            ><input
              v-model="draftSpecies"
              type="checkbox"
              :value="option.value"
            />{{ option.label }}</label
          >
        </div>
        <p v-if="!draftSpecies.length" class="sd-choice-hint">
          Choisissez au moins une espèce.
        </p>
        <div class="sd-dialog-actions">
          <button class="sv-button-quiet" @click="closeDialog">Annuler</button
          ><button
            class="sym-button"
            :disabled="!draftSpecies.length"
            @click="startRetrieval(draftSpecies)"
          >
            Confirmer
          </button>
        </div></template
      >
      <template v-else-if="dialog === 'import' && pendingImport"
        ><p>
          Fichier sélectionné : <strong>{{ pendingImport.filename }}</strong>
        </p>
        <p>
          Ajouter une entrée fictive au corpus
          {{ corpusSpeciesLabel(pendingImport.species) }} ? Seul le nom du
          fichier est utilisé. Aucun contenu ne sera lu, analysé, envoyé ou
          enregistré.
        </p>
        <div class="sd-dialog-actions">
          <button class="sv-button-quiet" @click="closeDialog">Annuler</button
          ><button class="sym-button" @click="confirmImport">
            Ajouter l’entrée de démonstration
          </button>
        </div></template
      >
      <template v-else-if="dialog === 'remove'"
        ><p>
          Retirer {{ selection.length }} entrée{{
            selection.length > 1 ? "s" : ""
          }}
          fictive{{ selection.length > 1 ? "s" : "" }} du corpus
          {{ corpusSpeciesLabel(species) }} ? Aucun fichier réel ne sera
          supprimé.
        </p>
        <div class="sd-dialog-actions">
          <button class="sv-button-quiet" @click="closeDialog">Annuler</button
          ><button
            class="sv-button-quiet sym-button-danger sd-remove"
            @click="removeSelection"
          >
            Confirmer le retrait simulé
          </button>
        </div></template
      >
      <template v-else-if="dialog === 'preview' && currentDocument"
        ><h3 class="sd-preview-title">{{ currentDocument.title }}</h3>
        <p>
          Cette entrée est fictive. Aucun texte scientifique authentique n’a été
          récupéré ou analysé et aucun fichier n’est ouvert.
        </p>
        <dl>
          <div>
            <dt>Espèce</dt>
            <dd>{{ corpusSpeciesLabel(currentDocument.species) }}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{{ currentDocument.kind }}</dd>
          </div>
          <div>
            <dt>Date fictive</dt>
            <dd>{{ currentDocument.date }}</dd>
          </div>
          <div v-if="currentDocument.filename">
            <dt>Nom local</dt>
            <dd>{{ currentDocument.filename }}</dd>
          </div>
        </dl></template
      >
    </DemoDialog>
  </GlassPanel>
</template>
