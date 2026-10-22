<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiUrl, message, percent, post, useResource } from "../api";
import type { Model, Operation, Report, Task, Video } from "../types";
const route = useRoute(),
  router = useRouter();
const videoId = ref(String(route.query.video || "")),
  taskId = ref(String(route.query.task || ""));
const video = useResource<Video>(() =>
  videoId.value ? `/console/videos/${videoId.value}` : null,
);
const tasks = useResource<Task[]>(() => "/console/tasks?kind=analysis", 5000);
const completed = ref(false),
  busy = ref(false),
  error = ref("");
const report = useResource<Report>(() =>
  completed.value ? `/console/tasks/${taskId.value}/artifacts/report` : null,
);
const reviewTask = ref("");
const isAdmin = computed(() => route.path.startsWith("/admin"));
const models = useResource<Model[]>(() => "/console/models", 15000);
const activeModel = computed(() =>
  models.data.value?.find((model) => model.active),
);
const preset = ref("balanced");
const modeChosen = ref(false);
watch(activeModel, (model) => {
  if (!modeChosen.value) config.value.detection_only = !model;
});
const config = ref({
  detection_only: true,
  detection_threshold: 0.1,
  classification_threshold: 0.48,
  track_threshold: 0.6,
  track_min_hits: 2,
  infer_every_n_frames: 2,
});
watch(
  () => route.query,
  (query) => {
    videoId.value = String(query.video || "");
    taskId.value = String(query.task || "");
    completed.value = false;
  },
);
const detections = computed(
  () =>
    report.data.value?.frames.flatMap((frame) =>
      frame.detections.map((d) => ({ ...d, time: frame.time_seconds })),
    ) ?? [],
);
async function launch() {
  busy.value = true;
  error.value = "";
  try {
    const operation = await post<Operation>(
      `/console/videos/${videoId.value}/analyze`,
      isAdmin.value
        ? config.value
        : {
            ...config.value,
            infer_every_n_frames: { detailed: 1, balanced: 2, fast: 10 }[
              preset.value as "detailed" | "balanced" | "fast"
            ],
          },
    );
    await router.replace({
      query: { video: videoId.value, task: operation.id },
    });
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function prepare() {
  busy.value = true;
  error.value = "";
  try {
    reviewTask.value = (
      await post<Operation>(`/console/videos/${videoId.value}/prepare-review`)
    ).id;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function loaded(task: Task) {
  completed.value = task.kind === "analysis";
  if (!videoId.value && task.request.video_id)
    videoId.value = task.request.video_id;
}
function prepared(task: Task) {
  if (task.result?.video_id)
    void router.push({
      path: "/review",
      query: { video_id: task.result.video_id },
    });
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">DÉTECTION · CLASSIFICATION · SUIVI</p>
      <h1>Analyse vidéo</h1>
      <p class="subtitle">
        Suivez chaque traitement et retrouvez ses résultats localisés.
      </p>
    </div>
    <RouterLink class="button-link secondary" to="/videos"
      >Choisir une vidéo <i class="pi pi-arrow-up-right"
    /></RouterLink>
  </div>
  <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  <div v-if="videoId" class="two-columns analysis-layout">
    <section class="panel">
      <LoadState
        :error="video.error.value"
        :loading="video.loading.value && !video.data.value"
        @retry="video.refresh"
        ><template v-if="video.data.value"
          ><h2>{{ video.data.value.filename }}</h2>
          <video
            class="video-player"
            controls
            preload="metadata"
            :src="apiUrl(`/console/videos/${videoId}/file`)"
          >
            <track kind="captions" />
          </video>
          <p class="muted">
            Espèce suggérée :
            {{ video.data.value.species_candidate || "Aucune" }}. Confirmation
            humaine requise.
          </p></template
        ></LoadState
      >
    </section>
    <section class="panel">
      <h2>Configurer l’analyse</h2>
      <form class="form-grid" @submit.prevent="launch">
        <label
          >Objectif de l'analyse<select
            v-model="config.detection_only"
            @change="modeChosen = true"
            :disabled="models.loading.value || !!models.error.value"
          >
            <option :value="false" :disabled="!activeModel">
              Identifier les espèces
            </option>
            <option :value="true">Détecter les animaux seulement</option>
          </select></label
        >
        <LoadState
          :loading="models.loading.value && !models.data.value"
          :error="models.error.value"
          @retry="models.refresh"
        />
        <p class="muted" v-if="activeModel">
          Modèle actif : {{ activeModel.name }}. Les espèces proposées restent à
          confirmer.
        </p>
        <p
          class="notice"
          v-else-if="!models.loading.value && !models.error.value"
        >
          Aucun classificateur actif. La détection reste disponible ;
          l'administration peut activer un modèle pour identifier les espèces.
        </p>
        <label v-if="!isAdmin"
          >Niveau de détail<select v-model="preset">
            <option value="balanced">Équilibré — une image sur 2</option>
            <option value="detailed">Détaillé — chaque image</option>
            <option value="fast">Rapide — une image sur 10</option>
          </select></label
        >
        <p v-if="!isAdmin" class="muted">
          Le mode rapide peut manquer un animal présent très brièvement. Les
          réglages techniques sont accessibles dans l'administration.
        </p>
        <div v-if="isAdmin" class="form-grid">
          <label
            >Seuil de détection<input
              type="number"
              v-model.number="config.detection_threshold"
              min="0.005"
              max="1"
              step="0.005"
              required /></label
          ><label
            >Seuil de classification<input
              type="number"
              v-model.number="config.classification_threshold"
              :disabled="config.detection_only"
              min="0"
              max="1"
              step="0.01"
              required /></label
          ><label
            >Confiance minimale des pistes<input
              type="number"
              v-model.number="config.track_threshold"
              min="0"
              max="1"
              step="0.01"
              required /></label
          ><label
            >Détections minimales par piste<input
              type="number"
              v-model.number="config.track_min_hits"
              min="1"
              max="100"
              required /></label
          ><label
            >Analyser une image sur<input
              type="number"
              v-model.number="config.infer_every_n_frames"
              min="1"
              max="1000"
              required
          /></label>
        </div>
        <PButton
          type="submit"
          label="Lancer l’analyse"
          icon="pi pi-play"
          :loading="busy"
          :disabled="busy || models.loading.value || !!models.error.value"
        /><PButton
          label="Préparer les recadrages à valider"
          severity="secondary"
          :disabled="busy"
          @click="prepare"
        />
      </form>
      <p class="muted">
        La classification utilise le modèle actif au lancement. La préparation
        des recadrages est une tâche distincte.
      </p>
    </section>
  </div>
  <TaskPanel v-if="taskId" :key="taskId" :id="taskId" @completed="loaded" />
  <TaskPanel v-if="reviewTask" :id="reviewTask" @completed="prepared" />
  <LoadState
    v-if="completed"
    :error="report.error.value"
    :loading="report.loading.value"
    @retry="report.refresh"
    ><template v-if="report.data.value"
      ><section class="panel">
        <h2>Vidéo annotée</h2>
        <video
          class="video-player"
          controls
          preload="metadata"
          :src="apiUrl(`/console/tasks/${taskId}/artifacts/video`)"
        >
          <track kind="captions" />
        </video>
        <div class="stat-grid compact">
          <div class="stat">
            <span>Images décodées</span
            ><strong>{{ report.data.value.frames_decoded }}</strong>
          </div>
          <div class="stat">
            <span>Détections</span
            ><strong>{{ report.data.value.detections }}</strong>
          </div>
          <div class="stat">
            <span>Temps GPU</span
            ><strong>{{
              report.data.value.diagnostics.gpu_elapsed_seconds == null
                ? "Non mesuré"
                : `${Number(report.data.value.diagnostics.gpu_elapsed_seconds).toFixed(2)} s`
            }}</strong>
          </div>
        </div>
        <p v-if="!detections.length" class="notice">
          Aucun animal détecté sur les images analysées. Le résultat est valide.
        </p>
      </section>
      <section class="panel">
        <h2>Détections localisées</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Temps</th>
                <th>Espèce / état</th>
                <th>Détection</th>
                <th>Classification</th>
                <th>Boîte xywh</th>
                <th>Piste</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, index) in detections.slice(0, 200)"
                :key="index"
              >
                <td>{{ item.time.toFixed(2) }} s</td>
                <td>
                  {{
                    item.classification?.label ||
                    {
                      detection_unclassified: "Non classée",
                      species_uncertain: "Espèce incertaine",
                    }[item.state] ||
                    item.state
                  }}
                </td>
                <td>{{ percent(item.detection_score) }}</td>
                <td>{{ percent(item.classification?.score) }}</td>
                <td class="mono">
                  {{
                    Object.values(item.box)
                      .map((value) => value.toFixed(3))
                      .join(" · ")
                  }}
                </td>
                <td>{{ item.track_id }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted">
          {{ detections.length }} détections au total. Les 200 premières sont
          affichées ; le JSON contient toutes les localisations.
        </p>
      </section></template
    ></LoadState
  >
  <section class="panel">
    <h2>Analyses précédentes</h2>
    <LoadState
      :error="tasks.error.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucune analyse lancée depuis la console"
      @retry="tasks.refresh"
      ><ul class="plain-list">
        <li v-for="task in tasks.data.value" :key="task.id">
          <RouterLink
            :to="{ query: { task: task.id, video: task.request.video_id } }"
            >Analyse {{ task.id.slice(0, 8) }}</RouterLink
          ><StatusBadge :status="task.status" />
        </li></ul
    ></LoadState>
  </section>
</template>
