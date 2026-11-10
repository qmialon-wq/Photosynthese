<script setup lang="ts">
import { apiUrl } from "../api";
import type {
  DesignAlternative,
  DesignProposal,
  TerritorialAnalysis,
  TerritorialSource,
} from "../territorial-context";
const props = defineProps<{
  proposals?: DesignProposal[];
  facts: TerritorialAnalysis["facts"];
  sources: TerritorialSource[];
  obsolete?: boolean;
}>();
const levels = {
  exploratory: "Exploratoire",
  contextualized: "Contextualisé",
  scientifically_qualified: "Scientifiquement qualifié · sous conditions",
};
function sourceLabel(source: TerritorialSource, option: DesignAlternative) {
  if (source.role === "general_design_reference")
    return "Référence générale de conception";
  if (source.applicability === "not_assessed")
    return "Extrait à examiner · applicabilité non établie";
  if (source.applicability === "reviewed")
    return option.justification.level === "scientifically_qualified" &&
      source.design_alternative_ids?.includes(option.id)
      ? "Appui scientifique examiné pour cette alternative"
      : "Source du thème · appui pour cette alternative à vérifier";
  return "Donnée de contexte";
}
function references(ids: string[]) {
  return props.sources.filter((source) => ids.includes(source.id));
}
</script>
<template>
  <section class="project-alternatives" aria-label="Adapter mon projet">
    <ol class="design-journey" aria-label="Parcours de conception">
      <li>Projet initial</li>
      <li>Alternatives à étudier</li>
      <li>Justifications</li>
      <li>Conditions et limites</li>
    </ol>
    <p>
      Comparez ces options conditionnelles au projet envisagé. Leur efficacité
      écologique locale et leur faisabilité restent à établir.
    </p>
    <p v-if="obsolete" class="notice">
      Ces options concernent les interventions figées dans l’analyse précédente.
      Relancez l’analyse pour examiner le projet modifié.
    </p>
    <p v-if="proposals === undefined" class="notice">
      Cette analyse historique ne contient pas encore d’alternatives de
      conception. Lancez une nouvelle analyse pour les obtenir.
    </p>
    <p v-else-if="!proposals.length" class="notice">
      Renseignez les interventions envisagées puis lancez une analyse pour
      explorer des alternatives adaptées au projet.
    </p>
    <article
      v-for="project in proposals"
      :key="project.project_action"
      class="design-project"
      :data-intervention="project.project_action"
    >
      <header class="design-initial">
        <p class="eyebrow">Projet initial déclaré</p>
        <h4>{{ project.initial_intervention }}</h4>
        <p><strong>Enjeu potentiel à examiner :</strong> {{ project.issue }}</p>
        <p class="muted">
          Le choix de l’intervention ne décrit pas encore son tracé, ses
          dimensions ou ses modalités.
        </p>
      </header>
      <div class="design-options">
        <article
          v-for="option in project.alternatives"
          :key="option.id"
          class="design-option"
          :data-alternative="option.id"
        >
          <p class="eyebrow">
            {{
              option.category === "avoid"
                ? "Évitement à étudier"
                : "Réduction à étudier"
            }}
            · option conditionnelle
          </p>
          <h5>{{ option.title }}</h5>
          <p>{{ option.proposal }}</p>
          <p>
            <strong>Ce que cela changerait au projet :</strong>
            {{ option.project_change }}
          </p>
          <p class="design-level">
            <strong
              >Niveau de justification :
              {{ levels[option.justification.level] }}</strong
            >
          </p>
          <p>{{ option.justification.reason }}</p>
          <p
            v-if="option.justification.level !== 'scientifically_qualified'"
            class="design-reserve"
          >
            Cette option ne dispose pas d’une justification scientifique
            qualifiée pour son application au site.
          </p>
          <h6>Conditions d’applicabilité</h6>
          <ul>
            <li v-for="condition in option.conditions" :key="condition">
              {{ condition }}
            </li>
          </ul>
          <details>
            <summary>Observations, sources mobilisées et limites</summary>
            <h6>Entrées mobilisées</h6>
            <ul>
              <li
                v-for="fact in facts.filter((item) =>
                  option.evidence_refs.includes(item.id),
                )"
                :key="fact.id"
              >
                {{ fact.text }}
              </li>
            </ul>
            <h6>Sources et portée des références</h6>
            <ul class="design-sources">
              <li
                v-for="source in references(option.source_refs)"
                :key="source.id"
              >
                <p>
                  <strong>{{ sourceLabel(source, option) }} :</strong>
                  <a
                    v-if="source.url?.startsWith('https://')"
                    :href="source.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ source.title }}</a
                  ><span v-else>{{ source.title }}</span>
                </p>
                <p v-if="source.quote || source.text">
                  {{ source.quote || source.text }}
                </p>
                <p v-if="source.page">Page {{ source.page }}</p>
                <p v-if="source.relevance_reason">
                  {{ source.relevance_reason }}
                </p>
                <a
                  v-if="source.original_url?.startsWith('/documents/')"
                  :href="apiUrl(source.original_url)"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Lire le document source</a
                >
              </li>
            </ul>
            <h6>Limites de l’option</h6>
            <ul>
              <li v-for="limit in option.limitations" :key="limit">
                {{ limit }}
              </li>
            </ul>
          </details>
        </article>
      </div>
    </article>
  </section>
</template>
<style scoped>
.design-journey {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  padding: 1rem 1rem 1rem 2rem;
  border-block: 1px solid #a4bfaa;
}
.design-journey li {
  padding-right: 1rem;
  font-weight: 700;
}
.design-project {
  margin-block: 1.5rem;
  border: 1px solid #a4bfaa;
  border-radius: 12px;
  overflow: hidden;
}
.design-initial {
  padding: 1rem;
  border-bottom: 1px solid #a4bfaa;
}
.design-initial h4 {
  margin-block: 0.4rem;
  font-size: 1.15rem;
}
.design-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 21rem), 1fr));
  align-items: start;
  gap: 1rem;
  padding: 1rem;
}
.design-option {
  border-left: 3px solid #bad58f;
  padding: 1rem;
  background: #102c2080;
  border-radius: 8px;
}
.design-option h5 {
  font-size: 1.1rem;
  margin-block: 0.5rem;
}
.design-option h6 {
  font-size: 0.95rem;
  margin-block: 1rem 0.5rem;
}
.design-level {
  padding: 0.5rem 0.75rem;
  border: 1px solid currentColor;
  border-radius: 8px;
  display: inline-block;
}
.design-reserve {
  font-style: italic;
}
.design-sources {
  overflow-wrap: anywhere;
}
@media (max-width: 600px) {
  .design-options,
  .design-initial,
  .design-option {
    padding: 0.75rem;
  }
}
</style>
