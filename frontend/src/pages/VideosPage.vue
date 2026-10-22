<script setup lang="ts">
import { ref } from "vue";
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
async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  busy.value = true;
  error.value = "";
  progress.value = 0;
  controller = new AbortController();
  try {
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
        (100 * Math.min(file.size, start + session.chunk_size)) / file.size,
      );
    }
    taskId.value = (
      await post<Operation>(`/console/uploads/${uploadId}/complete`)
    ).id;
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
  if (task.result?.video_id)
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
      ><i class="pi pi-plus" /> Importer une vidéo<input
        type="file"
        accept="video/*,.mkv,.avi,.m4v"
        :disabled="busy"
        aria-label="Importer une vidéo"
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
