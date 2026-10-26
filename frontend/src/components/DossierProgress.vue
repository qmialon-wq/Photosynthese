<script setup lang="ts">
import { computed } from "vue";
import { date } from "../api";
import type { DossierProgress } from "../dossier-progress";
const props = defineProps<{ progress?: DossierProgress | null }>();
const steps = [
  {
    key: "reading",
    title: "Lecture du corpus",
    description:
      "Examen des passages de chaque article et sélection des extraits utiles.",
  },
  {
    key: "recommendations",
    title: "Recommandations",
    description:
      "Croisement des sources par lots pour proposer des aménagements.",
  },
  {
    key: "consolidating",
    title: "Adaptation au territoire",
    description:
      "Arbitrage des mesures, conditions et priorités pour votre projet.",
  },
  {
    key: "writing",
    title: "Rédaction des quatre pages",
    description: "Rédaction et contrôle des citations page par page.",
  },
  {
    key: "checking",
    title: "Vérification finale",
    description: "Contrôle des sources avant l’enregistrement du dossier.",
  },
];
const active = computed(() =>
  steps.findIndex((s) => s.key === props.progress?.phase),
);
function duration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return minutes >= 60
    ? `${Math.floor(minutes / 60)} h ${minutes % 60} min`
    : minutes
      ? `${minutes} min`
      : "moins d’une minute";
}
</script>

<template>
  <section
    v-if="progress"
    class="rag-progress"
    aria-label="Avancement de la génération"
  >
    <h3>Avancement de votre dossier</h3>
    <p v-if="progress.reading_mode === 'balanced'" class="notice">
      Mode accéléré : tous les passages sont parcourus par analyse textuelle ;
      le modèle reçoit une sélection d’extraits par article pour élaborer les
      recommandations. La sélection peut manquer des nuances ou des résultats
      implicites.
      <span v-if="progress.generation_started_at"
        >Mode accéléré démarré :
        {{ date(progress.generation_started_at) }}.</span
      >
    </p>
    <p v-if="!progress.detailed_tracking" class="notice">
      Ce calcul a démarré avant l’ajout du suivi détaillé. Les compteurs sont
      reconstitués depuis son journal ; l’étape affichée est la dernière
      observée. Les étapes intermédiaires seront suivies plus précisément lors
      des prochaines générations.
    </p>
    <p v-if="progress.phase === 'queued'">
      En attente du moteur documentaire. Une tâche déjà en cours peut devoir se
      terminer avant le démarrage.
    </p>
    <p v-else-if="progress.phase === 'preparing'">
      Préparation du contexte de la parcelle et des espèces observées.
    </p>
    <p>
      Temps écoulé : {{ duration(progress.elapsed_seconds) }} · Dernière
      activité enregistrée : {{ date(progress.last_activity_at) }}
    </p>
    <ol class="rag-steps">
      <li
        v-for="(step, index) in steps"
        :key="step.key"
        :aria-current="index === active ? 'step' : undefined"
      >
        <strong
          >{{ index < active ? "✓ " : index === active ? "→ " : ""
          }}{{ step.title }}</strong
        >
        <span>{{
          index < active
            ? "Terminée"
            : index === active
              ? "En cours"
              : "À venir"
        }}</span>
        <p v-if="index === active">{{ step.description }}</p>
      </li>
    </ol>
    <template v-if="progress.documents_total !== undefined">
      <p>
        {{
          progress.documents_done ?? Math.max(0, progress.documents_started - 1)
        }}
        / {{ progress.documents_total }} articles entièrement examinés<span
          v-if="progress.documents_done === undefined"
        >
          (minimum confirmé)</span
        >.
      </p>
    </template>
    <p v-else>
      {{ progress.documents_started }} articles abordés. Le total n’a pas été
      enregistré au démarrage de cette génération.
    </p>
    <p>
      {{ progress.chunks_read
      }}<template v-if="progress.chunks_total !== undefined">
        / {{ progress.chunks_total }}</template
      >
      passages examinés.
    </p>
    <progress
      v-if="progress.chunks_total"
      :value="progress.chunks_read"
      :max="Math.max(progress.chunks_total, progress.chunks_read)"
      aria-label="Passages du corpus examinés"
    />
    <p v-if="progress.phase === 'reading' && progress.current_document">
      <strong>Article en cours :</strong> {{ progress.current_document }}
    </p>
    <p v-if="progress.groups_total !== undefined">
      Lots de recommandations contrôlés : {{ progress.groups_done }} /
      {{ progress.groups_total }}.
    </p>
    <p>
      Pages rédigées et contrôlées : {{ progress.pages_done }} /
      {{ progress.pages_total }}.
    </p>
    <p v-if="progress.seconds_since_activity > 900" class="notice">
      Aucune nouvelle étape enregistrée depuis
      {{ duration(progress.seconds_since_activity) }}. Un calcul peut être en
      cours ; cela ne permet pas à lui seul de conclure à un blocage.
    </p>
    <p class="muted">
      La lecture et la rédaction locales peuvent prendre plusieurs heures. Les
      compteurs avancent à la fin de chaque lot ; un calcul peut durer plusieurs
      minutes. Le temps restant n’est pas encore estimable. Vous pouvez fermer
      cette page, puis revenir.
    </p>
    <details v-if="progress.recent.length">
      <summary>Dernières étapes enregistrées</summary>
      <ul>
        <li v-for="(event, index) in progress.recent" :key="index">
          {{ date(event.at) }} · {{ event.message }}
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.rag-progress {
  padding: 1rem;
  border: 1px solid var(--border, #ccd7d1);
  border-radius: 0.75rem;
  margin: 1rem 0;
}
.rag-steps {
  padding-left: 1.5rem;
}
.rag-steps li {
  padding: 0.4rem;
}
.rag-steps li[aria-current="step"] {
  background: #edf5ee;
  border-radius: 0.4rem;
}
.rag-steps span {
  margin-left: 0.6rem;
  font-size: 0.9em;
}
.rag-steps p {
  margin: 0.3rem 0;
}
progress {
  width: 100%;
}
</style>
