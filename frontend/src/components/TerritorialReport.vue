<script setup lang="ts">
import { apiUrl, date } from "../api";
import type { TerritorialReport } from "../territorial";

defineProps<{ report: TerritorialReport; dossierId: string }>();
const priorities: Record<string, string> = {
  before_project: "Avant le projet",
  design: "Pendant la conception",
  works: "Pendant les travaux",
  monitoring: "Pendant le suivi",
};
</script>

<template>
  <section aria-label="Recommandations territoriales">
    <h3>Rapport d’aménagement du territoire</h3>
    <p>
      {{ report.coverage.documents_read }} /
      {{ report.coverage.documents_total }} documents examinés<span
        v-if="report.coverage.chunks_read != null"
      >
        · {{ report.coverage.chunks_read }} passages lus</span
      >.
      <span v-if="report.corpus_snapshot_at">
        Corpus figé au démarrage de l’analyse :
        {{ date(report.corpus_snapshot_at) }}.
      </span>
    </p>
    <p v-if="report.coverage.reading_method" class="notice">
      {{ report.coverage.reading_method }}
      <span v-if="report.coverage.excerpts_selected != null"
        >{{ report.coverage.excerpts_selected }} extraits retenus pour la
        synthèse.</span
      >
    </p>
    <p v-if="report.coverage.documents_pending_review" class="notice">
      {{ report.coverage.documents_pending_review }} document(s) restent en
      attente de validation scientifique. Les recommandations doivent être
      relues avant leur mise en œuvre.
    </p>
    <p v-if="report.coverage.batches_rejected?.length" class="notice">
      {{ report.coverage.batches_rejected.length }} lot(s) n’ont produit aucune
      proposition validée après correction. Leurs propositions ont été écartées
      ; les motifs figurent dans l’audit JSON. La synthèse ne doit pas être
      considérée comme complète sur ces lots.
    </p>
    <p v-if="report.coverage.unreadable_ids?.length" class="notice">
      {{ report.coverage.unreadable_ids.length }} fichier(s) sans texte
      extractible ne peuvent pas être analysés. La couverture du corpus est
      incomplète.
    </p>
    <p v-if="report.coverage.new_documents_since_snapshot" class="notice">
      {{ report.coverage.new_documents_since_snapshot }} document(s) ont été
      ajoutés pendant l’analyse. Actualisez le dossier pour les intégrer.
    </p>
    <template v-if="report.status === 'generated'">
      <div class="actions">
        <a
          class="button-link"
          :href="apiUrl(`/parcels/dossiers/${dossierId}/export?format=html`)"
          target="_blank"
          rel="noopener"
          >Ouvrir les 4 pages pour imprimer ou enregistrer en PDF</a
        >
        <a
          :href="apiUrl(`/parcels/dossiers/${dossierId}/export?format=json`)"
          download
          >Télécharger les références et l’audit complet</a
        >
      </div>
      <article v-for="(page, index) in report.pages" :key="index">
        <h4>{{ index + 1 }}. {{ page.title }}</h4>
        <p v-for="(paragraph, p) in page.paragraphs" :key="p">
          {{ paragraph.text }}
          <span class="muted">[{{ paragraph.citations.join("][") }}]</span>
        </p>
      </article>
      <h4>Fiches de mise en œuvre</h4>
      <details v-for="action in report.actions" :key="action.title">
        <summary>
          {{ action.title }} · {{ priorities[action.priority] }}
        </summary>
        <p>{{ action.action }}</p>
        <p><strong>Où :</strong> {{ action.location }}</p>
        <p><strong>Pourquoi :</strong> {{ action.rationale }}</p>
        <p><strong>Conditions :</strong> {{ action.conditions }}</p>
        <p><strong>Suivi :</strong> {{ action.monitoring }}</p>
        <p>Sources : [{{ action.citations.join("][") }}]</p>
      </details>
    </template>
    <p v-else class="notice">
      Le corpus examiné ne fournit pas assez d’éléments pertinents pour rédiger
      des recommandations spécifiques au projet.
    </p>
  </section>
</template>
