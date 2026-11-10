<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import SearchField from "../components/symbiose/SearchField.vue";
import FilterSelect from "../components/symbiose/FilterSelect.vue";
import Pagination from "../components/symbiose/Pagination.vue";
import DemoDialog from "../components/symbiose/DemoDialog.vue";
import StatusBadge from "../components/symbiose/StatusBadge.vue";
import ProjectCard from "../components/symbiose/ProjectCard.vue";
import {
  filterDemoProjects,
  projectStatusOptions,
  projectTypeOptions as seedProjectTypeOptions,
  type DemoProject,
} from "../data/project-preview";
// Réutilisation des styles des contrôles existants, sans copie ni modification.
import "../styles/videotheque.css";
import "../styles/dossiers.css";
import { useCollection } from "../data/data-mode";
import SourceState from "../components/symbiose/SourceState.vue";
const { items: projects, state: source, store } = useCollection("projects");
const router = useRouter();
function openProject(project: DemoProject) {
  if (store.isReal.value) {
    void router.push(`/parcelles/${encodeURIComponent(project.id)}`);
  } else current.value = project;
}
const projectTypeOptions = computed(() => [
  { value: "", label: "Tous les projets" },
  ...[
    ...new Set(
      projects.value.map((project) => project.project).filter(Boolean),
    ),
  ].map((value) => ({
    value,
    label:
      seedProjectTypeOptions.find((option) => option.value === value)?.label ||
      value,
  })),
]);
const query = ref(""),
  type = ref(""),
  status = ref(""),
  page = ref(1);
const current = ref<DemoProject | null>(null),
  feedback = ref("");
const filtered = computed(() =>
  filterDemoProjects(projects.value, query.value, type.value, status.value),
);
const visible = computed(() =>
  filtered.value.slice((page.value - 1) * 6, page.value * 6),
);
watch([query, type, status], () => {
  page.value = 1;
  feedback.value = "";
});
function refresh() {
  if (store.capabilities.value.readOnly) {
    void store.refresh();
    return;
  }
  query.value = "";
  type.value = "";
  status.value = "";
  page.value = 1;
  feedback.value = "Dossiers de démonstration actualisés.";
}
const projectLabel = computed(
  () =>
    projectTypeOptions.value.find(
      (option) => option.value === current.value?.project,
    )?.label,
);
</script>
<template>
  <GlassPanel
    depth="page"
    class="sv-page sf-page"
    topography
    aria-labelledby="sf-title"
  >
    <header class="sv-header sf-header">
      <div class="sv-heading">
        <span class="sv-heading-icon"
          ><SymIcon name="folder" :size="39"
        /></span>
        <div>
          <h1 id="sf-title">Mes dossiers</h1>
          <p>
            Regroupez les vidéos d’une même parcelle et décrivez votre projet
            une seule fois.
          </p>
        </div>
      </div>
      <RouterLink class="sym-button sv-import sf-create" to="/videos"
        ><SymIcon name="plus" :size="27" />Choisir ou importer des
        vidéos</RouterLink
      >
    </header>
    <SourceState
      :resource="source"
      empty-text="Aucun dossier enregistré."
      @retry="store.refresh"
    />
    <p v-if="store.capabilities.value.readOnly" class="sym-read-only">
      Ouvrez votre dossier pour compléter le projet, modifier la parcelle ou
      actualiser les recommandations.
    </p>
    <div class="sv-filters sf-filters">
      <SearchField
        v-model="query"
        label="Rechercher un dossier"
        placeholder="Rechercher un dossier…"
      /><FilterSelect
        v-model="type"
        label="Filtrer par projet"
        :options="projectTypeOptions"
      /><FilterSelect
        v-model="status"
        label="Filtrer par statut"
        :options="projectStatusOptions"
      /><button
        class="sv-refresh"
        aria-label="Actualiser les dossiers"
        @click="refresh"
      >
        <SymIcon name="refresh" :size="24" />
      </button>
    </div>
    <div v-if="visible.length" class="sf-project-grid">
      <ProjectCard
        v-for="project in visible"
        :key="project.id"
        :project="project"
        @open="openProject"
      />
    </div>
    <div v-else-if="source.state === 'success'" class="sv-empty sf-empty">
      <SymIcon name="folder" :size="36" />
      <h2>Aucun dossier ne correspond à votre recherche</h2>
      <p>Essayez un autre nom, un autre projet ou un autre statut.</p>
      <button class="sv-button-quiet" @click="refresh">
        Réinitialiser les filtres
      </button>
    </div>
    <Pagination
      :page="page"
      :total="filtered.length"
      :page-size="6"
      item-label="dossier"
      navigation-label="Pagination des dossiers"
      @change="page = $event"
    />
    <p v-if="feedback" class="sv-feedback" role="status">{{ feedback }}</p>
    <DemoDialog
      :notice="
        store.capabilities.value.readOnly
          ? 'DONNÉES RÉELLES · CONSULTATION'
          : undefined
      "
      :open="!!current"
      :title="current?.name || 'Dossier de démonstration'"
      @close="current = null"
    >
      <template v-if="current"
        ><div
          class="sf-project-photo sf-demo-photo"
          :class="
            current.landscape
              ? `sf-landscape-${current.landscape}`
              : 'sym-thumbnail-empty'
          "
          role="img"
          :aria-label="`Paysage du dossier ${current.name}`" />
        <StatusBadge
          class="sf-demo-status"
          :status="current.status"
          :label="current.status === 'validated' ? 'Validé' : undefined" />
        <p>
          {{
            store.capabilities.value.readOnly
              ? "Informations du dossier enregistré. Les champs absents sont indiqués par un tiret."
              : "Ce dossier présente des données fictives. Aucun traitement, stockage ou résultat métier réel n’est disponible dans cet aperçu."
          }}
        </p>
        <dl>
          <div>
            <dt>Projet</dt>
            <dd>{{ projectLabel || current.project || "—" }}</dd>
          </div>
          <div>
            <dt>Vidéos</dt>
            <dd>{{ current.videos ?? "—" }} vidéos</dd>
          </div>
          <div>
            <dt>Espèces</dt>
            <dd>{{ current.species ?? "—" }} espèces</dd>
          </div>
        </dl>
        <RouterLink class="sym-button sf-demo-action" to="/videos"
          >Choisir des vidéos<SymIcon name="arrow" :size="20" /></RouterLink
      ></template>
    </DemoDialog>
  </GlassPanel>
</template>
