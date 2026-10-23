<script setup lang="ts">
import { date, taskLabel, useResource } from "../api";
import type { Task } from "../types";
const tasks = useResource<Task[]>(
  () => "/console/tasks?kind=analysis&limit=5",
  5000,
);
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">BIOSENTINELLE NORMANDIE</p>
      <h1>Vos observations, simplement.</h1>
      <p class="subtitle">
        Ajoutez les vidéos d’une même parcelle, décrivez votre projet et
        retrouvez les vidéos annotées avec un dossier biodiversité commun.
      </p>
    </div>
    <RouterLink to="/videos" class="button-link"
      ><i class="pi pi-plus" aria-hidden="true" /> Importer une
      vidéo</RouterLink
    >
  </div>
  <div class="journey-grid">
    <RouterLink to="/videos" class="panel journey-card"
      ><span class="eyebrow">01 · IMPORTER</span
      ><i class="pi pi-video" aria-hidden="true" />
      <h2>Vos vidéos de terrain</h2>
      <p>Importez plusieurs vidéos ou sélectionnez celles de votre parcelle.</p>
      <span>Ouvrir la vidéothèque →</span></RouterLink
    >
    <RouterLink to="/parcelles" class="panel journey-card"
      ><span class="eyebrow">02 · DÉCRIRE VOTRE PROJET</span
      ><i class="pi pi-sparkles" aria-hidden="true" />
      <h2>Votre parcelle, votre projet</h2>
      <p>Indiquez la surface, le type de terrain et l’activité souhaitée.</p>
      <span>Voir les analyses →</span></RouterLink
    >
    <RouterLink to="/parcelles" class="panel journey-card"
      ><span class="eyebrow">03 · RETROUVER VOS RÉSULTATS</span
      ><i class="pi pi-check-square" aria-hidden="true" />
      <h2>Un dossier pour aménager</h2>
      <p>
        Confirmez les espèces, consultez les pistes sourcées et téléchargez
        votre dossier.
      </p>
      <span>Vidéo annotée et dossier →</span></RouterLink
    >
  </div>
  <section class="panel">
    <div class="section-head">
      <h2>Dernières analyses</h2>
      <RouterLink to="/analyses">Tout consulter</RouterLink>
    </div>
    <LoadState
      :loading="tasks.loading.value && !tasks.data.value"
      :error="tasks.error.value"
      :empty="tasks.data.value?.length === 0"
      empty-text="Aucune analyse pour le moment. Importez votre première vidéo pour commencer."
      @retry="tasks.refresh"
    >
      <ul class="plain-list">
        <li v-for="task in tasks.data.value" :key="task.id">
          <RouterLink
            :to="{
              path: '/analyses',
              query: { task: task.id, video: task.request.video_id },
            }"
            >{{ taskLabel(task.kind) }} · {{ task.id.slice(0, 8) }}</RouterLink
          ><span v-if="task.created_at" class="muted">{{
            date(task.created_at)
          }}</span
          ><StatusBadge :status="task.status" />
        </li>
      </ul>
    </LoadState>
  </section>
</template>
