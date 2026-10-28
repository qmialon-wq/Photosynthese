<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { taskLabel, useResource } from "../api";

interface WorkerTask {
  id: string;
  kind: string;
  status: string;
  priority?: number;
  detail: string | null;
  error: string | null;
  progress: { current?: number; total?: number; stage?: string };
  logs: { id: number; message: string; created_at: string }[];
}
interface Activity {
  updated_at: string;
  workers: {
    role: string;
    online: boolean | null;
    running: number;
    queued: number;
    tasks: WorkerTask[];
  }[];
}
const feed = useResource<Activity>(() => "/console/workers", 2000);
const follow = ref(true);
const output = ref<HTMLElement>();
const labels: Record<string, string> = {
  search: "Collecte scientifique",
  translate: "Traduction",
  rag: "RAG",
  fetch: "Téléchargement",
  import: "Import documentaire",
};
const label = (task: WorkerTask) => labels[task.kind] || taskLabel(task.kind);
const priorities = ["Client", "Entraînement", "Ressources RAG", "Traduction"];
const time = (value: string) => new Date(value).toLocaleTimeString("fr-FR");
const progress = (task: WorkerTask) =>
  task.progress.total && task.progress.current != null
    ? Math.max(
        0,
        Math.min(
          100,
          Math.round((100 * task.progress.current) / task.progress.total),
        ),
      )
    : null;
const lines = computed(() =>
  (feed.data.value?.workers || [])
    .flatMap((worker) =>
      worker.tasks.flatMap((task) =>
        task.logs.map((line) => ({
          ...line,
          key: `${worker.role}:${line.id}`,
          role: worker.role,
          task: task.id.slice(0, 8),
        })),
      ),
    )
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .slice(-100),
);
watch(lines, async () => {
  await nextTick();
  if (follow.value && output.value)
    output.value.scrollTop = output.value.scrollHeight;
});
</script>

<template>
  <section class="worker-terminal" aria-labelledby="worker-terminal-title">
    <header>
      <div>
        <span class="terminal-dot" aria-hidden="true" />
        <h2 id="worker-terminal-title">Activité des workers</h2>
      </div>
      <span class="terminal-update"
        >Actualisation · 2 s<span v-if="feed.data.value">
          · {{ time(feed.data.value.updated_at) }}</span
        ></span
      >
    </header>
    <p v-if="feed.error.value" class="terminal-error" role="alert">
      Suivi interrompu : {{ feed.error.value }}
      <button @click="feed.refresh">Réessayer</button>
    </p>
    <p v-else-if="!feed.data.value" class="terminal-wait">
      Connexion aux workers…
    </p>
    <div v-if="feed.data.value" class="worker-grid">
      <article v-for="worker in feed.data.value.workers" :key="worker.role">
        <div class="worker-heading">
          <strong>{{
            worker.role === "vision" ? "Vision · IA" : "Documents · RAG"
          }}</strong>
          <span :class="{ offline: worker.online !== true }">{{
            worker.online === null
              ? "État indisponible"
              : worker.online
                ? "En ligne"
                : "Sans signal récent"
          }}</span>
        </div>
        <p class="worker-counts">
          {{ worker.running }} en cours · {{ worker.queued }} en attente
        </p>
        <div
          v-for="task in worker.tasks.filter((t) => t.status === 'running')"
          :key="task.id"
          class="worker-task"
        >
          <div>
            <strong
              >{{ label(task)
              }}<small v-if="task.priority != null">
                · {{ priorities[task.priority] }}</small
              ></strong
            ><code>{{ task.id.slice(0, 8) }}</code>
          </div>
          <p v-if="task.detail">{{ task.detail }}</p>
          <p>
            {{
              task.progress.stage ||
              task.logs.at(-1)?.message ||
              "Traitement en cours"
            }}
          </p>
          <template v-if="progress(task) !== null"
            ><progress
              :value="progress(task)!"
              max="100"
              :aria-label="`Progression : ${label(task)}`"
            /><small
              >{{ progress(task) }} % · {{ task.progress.current }} /
              {{ task.progress.total }}</small
            ></template
          >
          <small v-else
            >Progression non chiffrée · derniers messages ci-dessous</small
          >
        </div>
        <p v-if="!worker.running" class="worker-idle">
          {{
            worker.online ? "Aucune tâche en cours." : "En attente du worker."
          }}
        </p>
        <p v-if="worker.queued" class="worker-next">
          À suivre :
          {{
            worker.tasks
              .filter((t) => t.status === "queued")
              .slice(0, 3)
              .map((t) => `${label(t)}${t.detail ? ` · ${t.detail}` : ""}`)
              .join(" / ")
          }}
        </p>
      </article>
    </div>
    <div class="terminal-toolbar">
      <span>Journal en direct</span
      ><label
        ><input v-model="follow" type="checkbox" /> Défilement
        automatique</label
      >
    </div>
    <div
      ref="output"
      class="terminal-output"
      role="region"
      aria-label="Derniers messages des workers"
      tabindex="0"
    >
      <p v-for="line in lines" :key="line.key">
        <time>{{ time(line.created_at) }}</time>
        <span class="terminal-role">[{{ line.role }}:{{ line.task }}]</span>
        {{ line.message }}
      </p>
      <p v-if="!lines.length" class="terminal-wait">
        {{
          feed.data.value ? "Aucun message récent." : "Chargement du journal…"
        }}
      </p>
    </div>
    <footer>
      Priorité : client → entraînements → ressources RAG → traductions ·
      <RouterLink to="/admin/training">Entraînements</RouterLink> ·
      <RouterLink to="/admin/documents">Documents scientifiques</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.worker-terminal {
  margin: 0 0 24px;
  overflow: hidden;
  border: 1px solid #29463c;
  border-radius: 14px;
  background: #101f1b;
  color: #dfede5;
}
header,
header > div,
.worker-heading,
.worker-task > div,
.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
header {
  padding: 16px 20px;
  border-bottom: 1px solid #2b4138;
  flex-wrap: wrap;
}
header > div {
  justify-content: flex-start;
}
h2 {
  margin: 0;
  color: #f0f8f2;
  font-size: 16px;
}
.terminal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #97d6ac;
}
.terminal-update,
.worker-counts,
small,
.worker-idle,
.worker-next,
footer {
  color: #afc7b9;
  font-size: 12px;
}
.worker-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: #2b4138;
}
article {
  background: #172922;
  padding: 16px 20px;
  min-width: 0;
}
.worker-heading {
  flex-wrap: wrap;
}
.worker-heading span {
  font-size: 11px;
  color: #a6e2b9;
}
.worker-heading .offline,
.terminal-error {
  color: #ffd397;
}
.worker-counts {
  margin: 4px 0 12px;
}
.worker-task {
  font-size: 13px;
  overflow-wrap: anywhere;
}
.worker-task p {
  margin: 5px 0;
}
code {
  color: #afc7b9;
  font-size: 11px;
}
progress {
  display: block;
  width: 100%;
  height: 6px;
  margin: 10px 0 5px;
  accent-color: #a0dbb4;
}
.worker-next {
  margin-bottom: 0;
  overflow-wrap: anywhere;
}
.terminal-toolbar {
  padding: 10px 20px;
  font-size: 12px;
  flex-wrap: wrap;
  border-bottom: 1px solid #2b4138;
}
.terminal-toolbar label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.terminal-output {
  height: 190px;
  overflow: auto;
  padding: 12px 20px;
  font:
    12px/1.8 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
.terminal-output p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
time {
  color: #a0b4a8;
}
.terminal-role {
  color: #a5dbb7;
}
.terminal-wait,
.terminal-error {
  padding: 0 20px;
}
.terminal-output .terminal-wait {
  padding: 0;
}
footer {
  padding: 10px 20px;
  border-top: 1px solid #2b4138;
}
footer a {
  color: #c0e6cc;
}
button {
  color: inherit;
  background: transparent;
  border: 1px solid currentColor;
  border-radius: 4px;
  cursor: pointer;
}
@media (max-width: 700px) {
  .worker-grid {
    grid-template-columns: 1fr;
  }
  .terminal-output {
    height: 220px;
  }
}
</style>
