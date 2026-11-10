<script setup lang="ts">
import { computed, ref, watch } from "vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import StatCard from "../components/symbiose/StatCard.vue";
import VideoCard from "../components/symbiose/VideoCard.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import SearchField from "../components/symbiose/SearchField.vue";
import FilterSelect from "../components/symbiose/FilterSelect.vue";
import Pagination from "../components/symbiose/Pagination.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import {
  filterDemoVideos,
  videoStatusOptions,
  type DemoVideo,
} from "../data/video-preview";
import "../styles/videotheque.css";
import { useCollection } from "../data/data-mode";
import SourceState from "../components/symbiose/SourceState.vue";
const { items: videos, state: source, store } = useCollection("videos");
const videoOverview = computed(() => store.summary.value.videoOverview);
const videoSpeciesOptions = computed(() => [
  { value: "", label: "Toutes les espèces" },
  ...[...new Set(videos.value.map((v) => v.species).filter(Boolean))].map(
    (value) => ({ value, label: value }),
  ),
]);
const query = ref(""),
  species = ref(""),
  status = ref(""),
  page = ref(1);
const selected = ref(new Set<string>());
const feedback = ref("");
const filtered = computed(() =>
  filterDemoVideos(videos.value, query.value, species.value, status.value),
);
const visible = computed(() =>
  filtered.value.slice((page.value - 1) * 4, page.value * 4),
);
const allSelected = computed(
  () =>
    visible.value.length > 0 &&
    visible.value.every((video) => selected.value.has(video.id)),
);
const partlySelected = computed(
  () =>
    !allSelected.value &&
    visible.value.some((video) => selected.value.has(video.id)),
);
const selection = computed(() =>
  videos.value.filter((video) => selected.value.has(video.id)),
);
watch([query, species, status], () => {
  page.value = 1;
  feedback.value = "";
});
function toggle(id: string) {
  if (selected.value.has(id)) selected.value.delete(id);
  else selected.value.add(id);
}
function togglePage() {
  const remove = allSelected.value;
  visible.value.forEach((video) => {
    if (remove) selected.value.delete(video.id);
    else selected.value.add(video.id);
  });
}
function refresh() {
  if (store.capabilities.value.readOnly) {
    void store.refresh();
    return;
  }
  query.value = "";
  species.value = "";
  status.value = "";
  page.value = 1;
  feedback.value = "Bibliothèque de démonstration actualisée.";
}
type DialogKind = "import" | "prepare" | "preview" | "details";
const dialog = ref<DialogKind | null>(null),
  currentVideo = ref<DemoVideo | null>(null),
  importNames = ref<string[]>([]);
const dialogTitle = computed(() =>
  dialog.value === "import"
    ? "Importer des vidéos"
    : dialog.value === "prepare"
      ? "Préparer un dossier"
      : dialog.value === "details"
        ? "Informations de la vidéo"
        : currentVideo.value?.filename || "Prévisualisation",
);
function open(kind: DialogKind, video?: DemoVideo) {
  dialog.value = kind;
  currentVideo.value = video || null;
  importNames.value = [];
}
function chooseFiles(event: Event) {
  importNames.value = Array.from(
    (event.target as HTMLInputElement).files || [],
  ).map((file) => file.name);
}
function finishDemo() {
  if (!store.capabilities.value.simulate) return;
  feedback.value =
    dialog.value === "import"
      ? `Simulation terminée : ${importNames.value.length} fichier(s) sélectionné(s). Aucun fichier n’a été envoyé.`
      : `Démonstration terminée avec ${selected.value.size} vidéo(s) sélectionnée(s). Aucun dossier réel n’a été créé.`;
  dialog.value = null;
}
</script>
<template>
  <GlassPanel
    depth="page"
    class="sv-page"
    topography
    aria-labelledby="sv-title"
  >
    <header class="sv-header">
      <div class="sv-heading">
        <span class="sv-heading-icon"><SymIcon name="video" :size="41" /></span>
        <div>
          <h1 id="sv-title">Vidéothèque</h1>
          <p>Importez vos captures. Gardez la trace de chaque observation.</p>
        </div>
      </div>
      <button
        class="sym-button sv-import"
        :disabled="!store.capabilities.value.simulate"
        @click="open('import')"
      >
        <SymIcon name="plus" :size="27" />Importer des vidéos
      </button>
    </header>
    <SourceState
      :resource="source"
      empty-text="Aucune vidéo disponible."
      @retry="store.refresh"
    />
    <p v-if="store.capabilities.value.readOnly" class="sym-read-only">
      Consultation en lecture seule. Import et création de dossier indisponibles
      dans cet écran.
    </p>
    <div class="sv-stats" aria-label="Indicateurs de la vidéothèque">
      <StatCard v-for="stat in videoOverview" :key="stat.label" v-bind="stat" />
    </div>
    <GlassPanel class="sv-prepare" topography
      ><div class="sv-prepare-copy">
        <SymIcon name="folder" :size="37" />
        <div>
          <h2>Un dossier pour plusieurs vidéos</h2>
          <p>
            Sélectionnez les vidéos d’une même parcelle, puis remplissez le
            formulaire une seule fois.
          </p>
        </div>
      </div>
      <div class="sv-prepare-actions">
        <button
          class="sym-button sv-prepare-button"
          :disabled="!store.capabilities.value.simulate || !selected.size"
          @click="open('prepare')"
        >
          <SymIcon name="folder" :size="20" />Préparer un dossier ({{
            selected.size
          }}
          vidéo{{ selected.size > 1 ? "s" : "" }})</button
        ><button
          class="sv-button-quiet"
          :disabled="!selected.size"
          @click="selected.clear()"
        >
          <SymIcon name="trash" :size="18" />Effacer la sélection</button
        ><RouterLink to="/parcelles" class="sv-button-quiet"
          ><SymIcon name="folder" :size="22" />Retrouver mes
          dossiers</RouterLink
        >
      </div></GlassPanel
    >
    <GlassPanel depth="inset" class="sv-library" aria-label="Bibliothèque vidéo"
      ><label class="sv-select-page"
        ><input
          type="checkbox"
          :checked="allSelected"
          :indeterminate="partlySelected"
          :disabled="!visible.length"
          @change="togglePage"
        />Sélectionner les vidéos de cette page</label
      >
      <div class="sv-filters">
        <SearchField v-model="query" /><FilterSelect
          v-model="species"
          label="Filtrer par espèce"
          :options="videoSpeciesOptions"
        /><FilterSelect
          v-model="status"
          label="Filtrer par statut"
          :options="videoStatusOptions"
        /><button
          class="sv-refresh"
          aria-label="Actualiser les vidéos"
          @click="refresh"
        >
          <SymIcon name="refresh" :size="23" />
        </button>
      </div>
      <div v-if="visible.length" class="sv-video-grid">
        <VideoCard
          v-for="video in visible"
          :key="video.id"
          :video="video"
          :selected="selected.has(video.id)"
          @toggle="toggle"
          @preview="open('preview', $event)"
          @details="open('details', $event)"
        />
      </div>
      <div v-else-if="source.state === 'success'" class="sv-empty">
        <SymIcon name="search" :size="30" />
        <h2>Aucune vidéo ne correspond à votre recherche</h2>
        <p>Essayez une autre espèce, un autre statut ou un autre nom.</p>
        <button class="sv-button-quiet" @click="refresh">
          Réinitialiser les filtres
        </button>
      </div>
      <Pagination
        :page="page"
        :total="filtered.length"
        :page-size="4"
        @change="page = $event"
    /></GlassPanel>
    <p v-if="feedback" class="sv-feedback" role="status">{{ feedback }}</p>
    <DemoDialog
      :notice="
        store.capabilities.value.readOnly
          ? 'DONNÉES RÉELLES · CONSULTATION'
          : undefined
      "
      :open="!!dialog"
      :title="dialogTitle"
      @close="dialog = null"
    >
      <template v-if="dialog === 'import'"
        ><p>
          Choisissez des fichiers pour essayer l’interface. Il s’agit d’une
          simulation : aucun fichier n’est envoyé et aucune vidéo n’est ajoutée
          à la bibliothèque.
        </p>
        <label class="sv-demo-file"
          >Sélectionner des fichiers vidéo<input
            type="file"
            multiple
            accept="video/*,.mkv,.avi,.m4v"
            @change="chooseFiles"
        /></label>
        <ul v-if="importNames.length" class="sv-demo-files">
          <li v-for="(name, i) in importNames" :key="i">{{ name }}</li>
        </ul>
        <button
          class="sym-button"
          :disabled="!importNames.length"
          @click="finishDemo"
        >
          Confirmer la simulation
        </button></template
      >
      <template v-else-if="dialog === 'prepare'"
        ><p>
          {{ selected.size }} vidéo{{
            selected.size > 1 ? "s" : ""
          }}
          sélectionnée{{ selected.size > 1 ? "s" : "" }}. Cet aperçu ne crée
          aucun dossier réel.
        </p>
        <ul class="sv-demo-files">
          <li v-for="video in selection" :key="video.id">
            {{ video.filename }} · {{ video.parcel }}
          </li>
        </ul>
        <button class="sym-button" @click="finishDemo">
          Terminer la démonstration
        </button></template
      >
      <template v-else-if="currentVideo"
        ><video
          v-if="currentVideo.source"
          class="sym-real-preview"
          :src="currentVideo.source"
          controls
          preload="metadata"
        />
        <div
          v-else
          class="sym-photo sv-demo-photo"
          :class="
            currentVideo.thumbnail
              ? `sv-photo-${currentVideo.thumbnail}`
              : 'sym-thumbnail-empty'
          "
          role="img"
          :aria-label="currentVideo.species"
        />
        <p class="sv-demo-warning">
          {{
            store.capabilities.value.readOnly
              ? "Informations enregistrées. Les champs absents sont indiqués par un tiret."
              : dialog === "preview"
                ? "Aperçu de démonstration : la lecture vidéo réelle n’est pas activée."
                : "Les informations ci-dessous sont fictives."
          }}
        </p>
        <RouterLink
          v-if="store.isReal.value"
          class="sym-button"
          :to="`/videos/${encodeURIComponent(currentVideo.id)}/dossier`"
          >Lire le dossier et les recommandations</RouterLink
        >
        <dl>
          <div>
            <dt>Fichier</dt>
            <dd>{{ currentVideo.filename }}</dd>
          </div>
          <div>
            <dt>Parcelle</dt>
            <dd>{{ currentVideo.parcel || "—" }}</dd>
          </div>
          <div>
            <dt>Espèce</dt>
            <dd>{{ currentVideo.species || "—" }}</dd>
          </div>
          <div>
            <dt>Date</dt>
            <dd>{{ currentVideo.date || "—" }}</dd>
          </div>
          <div>
            <dt>Durée</dt>
            <dd>{{ currentVideo.duration || "—" }}</dd>
          </div>
        </dl></template
      >
    </DemoDialog>
  </GlassPanel>
</template>
