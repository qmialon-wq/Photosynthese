<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, apiUrl, date, message, post, useResource } from "../api";
import type { Operation, Species, Task, Video } from "../types";
const router = useRouter();
const route = useRoute();
const search = ref(""),
  species = ref(""),
  status = ref(""),
  offset = ref(0);
const videos = useResource<Video[]>(
  () =>
    `/console/videos?q=${encodeURIComponent(search.value)}&species=${species.value}&offset=${offset.value}${status.value ? `&status=${status.value}` : ""}`,
  8000,
);
const classes = useResource<Species[]>(() => "/review/species");
const taskId = ref(""),
  error = ref(""),
  busy = ref(false),
  progress = ref(0),
  preview = ref<Video | null>(null);
const localPath = ref("");
let controller: AbortController | null = null;
let uploadId = "";
const picked = ref<string[]>([]),
  importTasks = ref<Array<{ id: string; filename: string }>>([]),
  batchMode = ref(false),
  creating = ref(false);
type ImportState = {
  id: string;
  status: string;
  error: string | null;
  result: { video_id?: string } | null;
};
const importStates = ref<Record<string, ImportState>>({});
const importsPending = computed(
  () =>
    batchMode.value &&
    importTasks.value.some(
      (t) =>
        !["completed", "error", "cancelled"].includes(
          importStates.value[t.id]?.status || "",
        ),
    ),
);
const seenCompleted = new Set<string>();
let polling = false,
  disposed = false,
  pollTimer: ReturnType<typeof setInterval>;
const pollAbort = new AbortController();
async function pollImports() {
  if (
    !batchMode.value ||
    !importTasks.value.length ||
    !importsPending.value ||
    polling ||
    disposed
  )
    return;
  polling = true;
  try {
    const rows = await api<ImportState[]>("/parcels/import-status", {
      method: "POST",
      body: JSON.stringify({ task_ids: importTasks.value.map((t) => t.id) }),
      signal: pollAbort.signal,
    });
    if (disposed) return;
    let refresh = false;
    for (const row of rows) {
      importStates.value[row.id] = row;
      if (
        row.status === "completed" &&
        row.result?.video_id &&
        !seenCompleted.has(row.id)
      ) {
        seenCompleted.add(row.id);
        picked.value = [
          ...new Set([...picked.value, row.result.video_id]),
        ].slice(0, 1000);
        refresh = true;
      }
    }
    if (refresh) await videos.refresh();
  } catch (reason) {
    if (!disposed) error.value = message(reason);
  } finally {
    polling = false;
  }
}
watch(
  () => importTasks.value.length,
  (value) => {
    if (value === 1) void pollImports();
  },
);
onMounted(() => {
  pollTimer = setInterval(() => {
    if (!document.hidden) void pollImports();
  }, 3000);
});
onBeforeUnmount(() => {
  disposed = true;
  clearInterval(pollTimer);
  pollAbort.abort();
});
const allPicked = computed(
  () =>
    !!videos.data.value?.length &&
    videos.data.value.every((v) => picked.value.includes(v.id)),
);
function togglePage() {
  const current = videos.data.value?.map((v) => v.id) || [];
  picked.value = allPicked.value
    ? picked.value.filter((id) => !current.includes(id))
    : [...new Set([...picked.value, ...current])].slice(0, 1000);
}
async function createCorpus() {
  creating.value = true;
  error.value = "";
  try {
    const corpus = await post<{ id: string }>("/parcels/corpora", {
      video_ids: picked.value,
    });
    await router.push(`/parcelles/${corpus.id}`);
  } catch (reason) {
    error.value = message(reason);
  } finally {
    creating.value = false;
  }
}
async function upload(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || []);
  if (!files.length) return;
  if (files.length > 1000) {
    error.value = "Importez au maximum 1000 vidéos par lot.";
    return;
  }
  batchMode.value = files.length > 1 || picked.value.length > 0;
  importTasks.value = [];
  importStates.value = {};
  seenCompleted.clear();
  taskId.value = "";
  busy.value = true;
  error.value = "";
  progress.value = 0;
  controller = new AbortController();
  try {
    const total = files.reduce((sum, file) => sum + file.size, 0);
    let transferred = 0;
    for (const file of files) {
      const session = await post<{ id: string; chunk_size: number }>(
        "/console/uploads",
        { filename: file.name, size: file.size },
      );
      uploadId = session.id;
      for (
        let start = 0, index = 0;
        start < file.size;
        start += session.chunk_size, index++
      ) {
        await api(`/console/uploads/${uploadId}/chunks/${index}`, {
          method: "PUT",
          body: file.slice(start, start + session.chunk_size),
          signal: controller.signal,
        });
        progress.value = Math.round(
          (100 *
            (transferred + Math.min(file.size, start + session.chunk_size))) /
            total,
        );
      }
      const imported = (
        await post<Operation>(`/console/uploads/${uploadId}/complete`)
      ).id;
      importTasks.value.push({ id: imported, filename: file.name });
      transferred += file.size;
    }
  } catch (reason) {
    error.value = controller?.signal.aborted
      ? "Transfert annulé."
      : message(reason);
  } finally {
    busy.value = false;
    (event.target as HTMLInputElement).value = "";
  }
}
async function cancelUpload() {
  controller?.abort();
  if (uploadId) {
    try {
      await api(`/console/uploads/${uploadId}`, { method: "DELETE" });
    } catch (reason) {
      error.value = message(reason);
    }
  }
}
async function local() {
  batchMode.value = false;
  busy.value = true;
  error.value = "";
  try {
    taskId.value = (
      await post<Operation>("/console/videos/local", { video: localPath.value })
    ).id;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function prepared(task: Task) {
  await videos.refresh();
  if (task.result?.video_id && batchMode.value) {
    picked.value = [...new Set([...picked.value, task.result.video_id])].slice(
      0,
      1000,
    );
  } else if (task.result?.video_id)
    void router.push({
      path: "/analyses",
      query: { video: task.result.video_id },
    });
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">DONNÉES DE TERRAIN</p>
      <h1>Vidéothèque</h1>
      <p class="subtitle">
        Importez vos captures. Gardez la trace de chaque observation.
      </p>
    </div>
    <label class="button-link upload-button"
      ><i class="pi pi-plus" /> Importer des vidéos<input
        type="file"
        multiple
        accept="video/*,.mkv,.avi,.m4v"
        :disabled="busy || importsPending"
        aria-label="Importer une ou plusieurs vidéos"
        @change="upload"
    /></label>
  </div>
  <div v-if="busy" class="panel">
    <p role="status">Transfert : {{ progress }} %</p>
    <PProgressBar :value="progress" /><PButton
      label="Annuler le transfert"
      severity="secondary"
      @click="cancelUpload"
    />
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <TaskPanel v-if="taskId" :id="taskId" @completed="prepared" />
  <div v-for="item in batchMode ? [] : importTasks" :key="item.id">
    <p>{{ item.filename }}</p>
    <TaskPanel :id="item.id" @completed="prepared" />
  </div>
  <section
    v-if="batchMode && importTasks.length"
    class="panel"
    aria-label="Import du corpus"
  >
    <h2>Import des vidéos</h2>
    <p role="status">
      {{ seenCompleted.size }} / {{ importTasks.length }} vidéos prêtes.
    </p>
    <details>
      <summary>Voir le détail des imports</summary>
      <ul>
        <li v-for="item in importTasks" :key="item.id">
          {{ item.filename }} ·
          {{
            importStates[item.id]?.status === "completed"
              ? "Prête"
              : importStates[item.id]?.status === "error"
                ? "Échec de l’import"
                : "Préparation en cours"
          }}
          <p
            v-if="importStates[item.id]?.error"
            role="alert"
            class="notice error"
          >
            {{ importStates[item.id].error }}
          </p>
        </li>
      </ul>
    </details>
    <p
      v-if="
        Object.values(importStates).some((s) =>
          ['error', 'cancelled'].includes(s.status),
        )
      "
      class="notice error"
      role="alert"
    >
      Certains imports ont échoué ou ont été annulés. Ils ne font pas partie de
      la sélection. Réimportez ces fichiers pour constituer le corpus complet.
    </p>
  </section>
  <section class="panel" aria-label="Vidéos du dossier">
    <h2>Un dossier pour plusieurs vidéos</h2>
    <p>
      Sélectionnez les vidéos d’une même parcelle, puis remplissez le formulaire
      une seule fois.
    </p>
    <div class="actions">
      <PButton
        :label="`Préparer un dossier (${picked.length} vidéo${picked.length > 1 ? 's' : ''})`"
        :loading="creating"
        :disabled="busy || creating || importsPending || !picked.length"
        @click="createCorpus"
      /><PButton
        label="Effacer la sélection"
        severity="secondary"
        :disabled="!picked.length"
        @click="picked = []"
      /><RouterLink to="/parcelles">Retrouver mes dossiers</RouterLink>
    </div>
  </section>
  <details v-if="route.path.startsWith('/admin')" class="panel">
    <summary>Indexer une vidéo déjà déposée dans le dossier local</summary>
    <form class="inline-form" @submit.prevent="local">
      <label
        >Chemin relatif à data/datasets/inbox<input
          v-model="localPath"
          placeholder="camera-A/chevreuil.mp4"
          required /></label
      ><PButton type="submit" label="Indexer" :disabled="busy" />
    </form>
  </details>
  <section class="panel">
    <label class="check-line"
      ><input type="checkbox" :checked="allPicked" @change="togglePage" />
      Sélectionner les vidéos de cette page</label
    >
    <div class="toolbar">
      <label class="search-field"
        ><i class="pi pi-search" /><input
          v-model="search"
          placeholder="Rechercher une vidéo…"
          aria-label="Rechercher une vidéo"
          @input="offset = 0" /></label
      ><select
        v-model="species"
        aria-label="Espèce provisoire"
        @change="offset = 0"
      >
        <option value="">Toutes les espèces</option>
        <option
          v-for="item in classes.data.value"
          :key="item.name"
          :value="item.name"
        >
          {{ item.name }}
        </option></select
      ><select v-model="status" aria-label="Statut vidéo">
        <option value="">Tous les statuts</option>
        <option value="ready">Disponibles</option>
        <option value="no_detections">Sans détection</option>
        <option value="error">En erreur</option></select
      ><PButton
        icon="pi pi-refresh"
        aria-label="Actualiser les vidéos"
        severity="secondary"
        @click="videos.refresh"
      />
    </div>
    <LoadState
      :loading="videos.loading.value && !videos.data.value"
      :error="videos.error.value"
      :empty="videos.data.value?.length === 0"
      empty-text="Aucune vidéo dans cette sélection"
      @retry="videos.refresh"
    >
      <div class="video-grid">
        <article
          v-for="video in videos.data.value"
          :key="video.id"
          class="video-card"
        >
          <label class="check-line"
            ><input
              v-model="picked"
              type="checkbox"
              :value="video.id"
              :aria-label="`Sélectionner ${video.filename}`"
              :disabled="picked.length >= 1000 && !picked.includes(video.id)"
            />
            Inclure dans le dossier</label
          >
          <button
            class="video-thumbnail"
            :aria-label="`Prévisualiser ${video.filename}`"
            @click="preview = video"
          >
            <i class="pi pi-play-circle" /><span>Prévisualiser</span>
          </button>
          <div class="video-info">
            <div class="section-head">
              <StatusBadge :status="video.status" /><small>{{
                video.metadata.duration_seconds
                  ? `${Math.round(video.metadata.duration_seconds)} s`
                  : "Durée non mesurée"
              }}</small>
            </div>
            <h3 :title="video.filename">{{ video.filename }}</h3>
            <p>
              <i class="pi pi-globe" />
              {{ video.species_candidate || "Espèce non identifiée" }}
              <span class="muted">· provisoire</span>
            </p>
            <small>{{ date(video.created_at) }}</small
            ><RouterLink
              :to="{ path: '/analyses', query: { video: video.id } }"
              class="card-link"
              >Ouvrir l’analyse <i class="pi pi-arrow-right"
            /></RouterLink>
          </div>
        </article>
      </div>
    </LoadState>
    <div class="pagination">
      <PButton
        label="Précédent"
        severity="secondary"
        :disabled="offset === 0"
        @click="offset = Math.max(0, offset - 50)"
      /><span>Page {{ offset / 50 + 1 }}</span
      ><PButton
        label="Suivant"
        severity="secondary"
        :disabled="(videos.data.value?.length ?? 0) < 50"
        @click="offset += 50"
      />
    </div>
  </section>
  <p class="muted">
    L’espèce extraite du nom reste une suggestion. Aucun animal n’est validé
    automatiquement à l’import.
  </p>
  <PDialog
    :visible="!!preview"
    :header="preview?.filename"
    modal
    :style="{ width: 'min(960px,95vw)' }"
    @update:visible="preview = null"
    ><video
      v-if="preview"
      class="video-player"
      controls
      preload="metadata"
      :src="apiUrl(`/console/videos/${preview.id}/file`)"
    >
      <track kind="captions" />
    </video>
    <p class="muted">
      Si le codec source n’est pas lisible, téléchargez le fichier original.
    </p>
    <a
      v-if="preview"
      :href="apiUrl(`/console/videos/${preview.id}/file`)"
      download
      >Télécharger la vidéo</a
    ></PDialog
  >
</template>
