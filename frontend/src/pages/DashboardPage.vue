<script setup lang="ts">
import { date, percent, taskLabel, useResource } from "../api";
import type { Dashboard, Task } from "../types";
import WorkerTerminal from "../components/WorkerTerminal.vue";
const dashboard = useResource<Dashboard>(() => "/console/dashboard", 10000);
const tasks = useResource<Task[]>(() => "/console/tasks?limit=6", 4000);
const cards = [
  { key: "videos", label: "Vidéos uniques", icon: "pi-video" },
  { key: "species", label: "Espèces validées", icon: "pi-globe" },
  { key: "pending", label: "Recadrages à revoir", icon: "pi-check-square" },
  { key: "tasks", label: "Tâches actives", icon: "pi-bolt" },
] as const;
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">OBSERVATOIRE LOCAL · NORMANDIE</p>
      <h1>La biodiversité, en perspective.</h1>
      <p class="subtitle">Des observations de terrain aux données vérifiées.</p>
    </div>
    <RouterLink to="/videos" class="button-link"
      ><i class="pi pi-plus" /> Importer une vidéo</RouterLink
    >
  </div>
  <WorkerTerminal />
  <LoadState
    :error="dashboard.error.value"
    :loading="dashboard.loading.value && !dashboard.data.value"
    @retry="dashboard.refresh"
  >
    <template v-if="dashboard.data.value">
      <div class="stat-grid">
        <article v-for="card in cards" :key="card.key" class="stat">
          <div class="stat-top">
            <span>{{ card.label }}</span
            ><i :class="['pi', card.icon]" />
          </div>
          <strong>{{ dashboard.data.value.counts[card.key] }}</strong
          ><small v-if="card.key === 'species'"
            >sur les 10 espèces du manifeste</small
          ><small v-else-if="card.key === 'tasks'"
            >tâches lancées depuis la console</small
          ><small v-else-if="card.key === 'videos'"
            >Contenus distincts par SHA-256</small
          >
          <small v-else>Source : base locale</small>
        </article>
      </div>
      <section class="observation-banner">
        <div>
          <span class="eyebrow">CHAQUE OBSERVATION COMPTE</span>
          <h2>Donnez du sens aux images.</h2>
          <p>
            Une espèce suggérée reste à confirmer.<br />Votre validation
            construit les prochains datasets.
          </p>
          <RouterLink to="/review"
            >Ouvrir la file de validation <i class="pi pi-arrow-right"
          /></RouterLink>
        </div>
        <div class="contours" aria-hidden="true"><i class="pi pi-globe" /></div>
      </section>
      <div class="two-columns">
        <section class="panel">
          <div class="section-head">
            <h2>Espèces confirmées</h2>
            <RouterLink to="/datasets"
              >Datasets <i class="pi pi-arrow-up-right"
            /></RouterLink>
          </div>
          <div
            v-if="dashboard.data.value.distribution.length"
            class="distribution"
          >
            <div
              v-for="species in dashboard.data.value.distribution"
              :key="species.label"
            >
              <div>
                <span class="species-name">{{ species.label }}</span
                ><strong>{{ species.count }}</strong>
              </div>
              <progress
                :value="species.count"
                :max="
                  Math.max(
                    ...dashboard.data.value.distribution.map(
                      (row) => row.count,
                    ),
                  )
                "
                :aria-label="`${species.label} : ${species.count} recadrages validés`"
              />
            </div>
          </div>
          <div v-else class="empty">
            <i class="pi pi-globe" />
            <h3>Les premières validations arrivent.</h3>
            <p>Aucune espèce confirmée pour le moment.</p>
          </div>
        </section>
        <section class="panel">
          <div class="section-head">
            <h2>Dernier entraînement</h2>
            <RouterLink to="/training"
              >Consulter <i class="pi pi-arrow-up-right"
            /></RouterLink>
          </div>
          <template v-if="dashboard.data.value.latest_training"
            ><div class="measure">
              <span>Meilleur macro-F1 de validation</span
              ><strong>{{
                percent(dashboard.data.value.latest_training.best_macro_f1)
              }}</strong>
            </div>
            <p class="muted">
              Run :
              {{
                dashboard.data.value.latest_training.run_id || "Non renseigné"
              }}
            </p>
            <dl class="facts">
              <div>
                <dt>Matériel</dt>
                <dd>
                  {{
                    dashboard.data.value.latest_training.device ||
                    "Non renseigné"
                  }}
                </dd>
              </div>
              <div>
                <dt>Phase</dt>
                <dd>
                  {{
                    dashboard.data.value.latest_training.phase ||
                    "Non renseignée"
                  }}
                </dd>
              </div>
              <div>
                <dt>Pic mémoire GPU</dt>
                <dd>
                  {{
                    dashboard.data.value.latest_training
                      .gpu_peak_allocated_bytes != null
                      ? `${(dashboard.data.value.latest_training.gpu_peak_allocated_bytes / 1024 ** 3).toFixed(2)} Go`
                      : "Non mesuré"
                  }}
                </dd>
              </div>
            </dl></template
          >
          <div v-else class="empty">
            <i class="pi pi-chart-line" />
            <h3>Aucun entraînement enregistré.</h3>
            <p>Les performances apparaîtront après un premier run.</p>
          </div>
        </section>
      </div>
    </template>
  </LoadState>
  <section class="panel">
    <div class="section-head">
      <h2>Activité récente</h2>
      <RouterLink to="/analyses"
        >Voir les analyses <i class="pi pi-arrow-up-right"
      /></RouterLink>
    </div>
    <LoadState
      :error="tasks.error.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucune tâche lancée depuis la console"
      @retry="tasks.refresh"
      ><div class="table-scroll" v-if="tasks.data.value?.length">
        <table>
          <thead>
            <tr>
              <th scope="col">Traitement</th>
              <th scope="col">Statut</th>
              <th scope="col">Utilisateur</th>
              <th scope="col">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks.data.value" :key="task.id">
              <td>
                <RouterLink
                  :to="{
                    path: task.kind === 'training' ? '/training' : '/analyses',
                    query: { task: task.id },
                  }"
                  >{{ taskLabel(task.kind) }}
                  <span class="muted">{{
                    task.id.slice(0, 8)
                  }}</span></RouterLink
                >
              </td>
              <td><StatusBadge :status="task.status" /></td>
              <td>{{ task.actor }}</td>
              <td>{{ date(task.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div></LoadState
    >
  </section>
</template>
