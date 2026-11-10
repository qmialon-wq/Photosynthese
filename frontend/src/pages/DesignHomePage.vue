<script setup lang="ts">
import { computed } from "vue";
import { journey } from "../data/home-preview";
import { useDataMode } from "../data/data-mode";
import SourceState from "../components/symbiose/SourceState.vue";
const store = useDataMode();
const overview = computed(() => store.summary.value.overview);
const indicators = computed(() => store.summary.value.indicators);
const latestAnalyses = computed(() => store.summary.value.latestAnalyses);
const recommendation = computed(() => store.summary.value.recommendations[0]);
const notices = computed(() => [
  ...new Map(
    Object.values(store.data)
      .filter((source) =>
        ["error", "unconnected", "loading"].includes(source.state),
      )
      .map((source) => [source.message || source.state, source]),
  ).values(),
]);
import StatCard from "../components/symbiose/StatCard.vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import PillButton from "../components/symbiose/PillButton.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
import StatusBadge from "../components/symbiose/StatusBadge.vue";
import VideoThumbnail from "../components/VideoThumbnail.vue";
</script>
<template>
  <div class="sym-home">
    <h1 class="sym-sr-only">Accueil Symbiose</h1>
    <div class="sym-overview" aria-label="Indicateurs de suivi">
      <StatCard v-for="stat in overview" :key="stat.label" v-bind="stat" />
    </div>
    <template v-for="(source, key) in notices" :key="key">
      <SourceState
        v-if="
          source.state === 'error' ||
          source.state === 'unconnected' ||
          source.state === 'loading'
        "
        :resource="source"
        @retry="store.refresh"
      />
    </template>
    <div class="sym-journey">
      <GlassPanel
        v-for="card in journey"
        :key="card.step"
        as="article"
        class="sym-journey-card"
        topography
        ><p class="sym-eyebrow">{{ card.step }}</p>
        <span
          class="sym-journey-icon"
          :class="{ 'has-background': card.icon === 'video' }"
          ><SymIcon :name="card.icon" :size="32"
        /></span>
        <h2>{{ card.title }}</h2>
        <p class="sym-journey-description">{{ card.description }}</p>
        <PillButton :to="card.path">{{ card.action }}</PillButton></GlassPanel
      >
    </div>
    <div class="sym-insights">
      <GlassPanel
        v-if="store.isDemo.value"
        class="sym-diagnostic"
        aria-labelledby="diagnostic-heading"
      >
        <h2 id="diagnostic-heading" class="sym-panel-title">
          <span><SymIcon name="leaf" :size="25" /></span>Diagnostic écologique
        </h2>
        <div class="sym-diagnostic-body">
          <div
            class="sym-gauge"
            role="img"
            :aria-label="
              store.summary.value.score == null
                ? 'Diagnostic écologique non disponible'
                : `État écologique de démonstration : ${store.summary.value.score} sur 100`
            "
          >
            <svg viewBox="0 0 250 140" fill="none" aria-hidden="true">
              <defs>
                <linearGradient
                  id="sym-gauge-gradient"
                  x1="20"
                  y1="120"
                  x2="215"
                  y2="30"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stop-color="var(--sym-shade-accent-9ff63b)" />
                  <stop offset=".65" stop-color="var(--sym-shade-accent-bafa77)" />
                  <stop offset="1" stop-color="var(--sym-shade-accent-d6ffd2)" />
                </linearGradient>
              </defs>
              <path
                d="M25 119A100 100 0 0 1 225 119"
                stroke="#ffffff"
                stroke-opacity=".25"
                stroke-width="17"
                stroke-linecap="round"
                pathLength="100"
              />
              <path
                d="M25 119A100 100 0 0 1 225 119"
                stroke="url(#sym-gauge-gradient)"
                stroke-width="17"
                stroke-linecap="round"
                pathLength="100"
                :stroke-dasharray="`${store.summary.value.score ?? 0} 100`"
              />
            </svg>
            <div>
              <strong>{{ store.summary.value.score ?? "—" }}</strong
              ><span>/100</span>
              <p>
                {{
                  store.summary.value.score == null
                    ? "Non disponible"
                    : "État écologique"
                }}
              </p>
            </div>
          </div>
          <div class="sym-indicators">
            <div
              v-for="indicator in indicators"
              :key="indicator.label"
              class="sym-indicator"
            >
              <SymIcon :name="indicator.icon" :size="20" /><span>{{
                indicator.label
              }}</span>
              <div
                class="sym-meter"
                role="meter"
                :aria-label="indicator.label"
                :aria-valuenow="indicator.value"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <span :style="{ width: `${indicator.value}%` }" />
              </div>
              <span class="sym-indicator-value">{{ indicator.value }} %</span>
            </div>
          </div>
        </div>
      </GlassPanel>
      <GlassPanel
        class="sym-recommendation"
        aria-labelledby="recommendation-heading"
        ><h2 id="recommendation-heading" class="sym-panel-title">
          <span><SymIcon name="sprout" :size="25" /></span>Recommandation
          {{ store.isDemo.value ? "prioritaire" : "issue de vos dossiers" }}
        </h2>
        <div v-if="recommendation" class="sym-recommendation-body">
          <div
            class="sym-photo sym-photo-hedgerow"
            role="img"
            aria-label="Haies et prairie normandes"
          />
          <div>
            <h3>{{ recommendation.title }}</h3>
            <p>{{ recommendation.description }}</p>
          </div>
          <RouterLink
            :to="
              recommendation.projectId
                ? `/parcelles/${encodeURIComponent(recommendation.projectId)}`
                : '/parcelles'
            "
            class="sym-recommendation-next"
            :aria-label="`Lire le dossier : ${recommendation.title}`"
            ><SymIcon name="arrow" :size="23"
          /></RouterLink>
        </div>
        <div v-else class="sym-data-unavailable">
          Aucune recommandation disponible dans les dossiers consultés.
          <RouterLink to="/parcelles">Consulter mes dossiers</RouterLink>
        </div>
        <div
          v-if="recommendation && store.isDemo.value"
          class="sym-carousel-dots"
          aria-hidden="true"
        >
          <span class="is-active" /><span /><span /></div
      ></GlassPanel>
    </div>
    <GlassPanel class="sym-latest" aria-labelledby="latest-heading"
      ><div class="sym-latest-header">
        <h2 id="latest-heading">Dernières analyses</h2>
        <RouterLink to="/analyses"
          >Tout consulter<SymIcon name="arrow" :size="22"
        /></RouterLink>
      </div>
      <SourceState
        :resource="store.data.analyses"
        empty-text="Aucune analyse enregistrée."
        @retry="store.refresh" />
      <ul v-if="latestAnalyses.length" class="sym-analysis-list">
        <li v-for="analysis in latestAnalyses" :key="analysis.name">
          <RouterLink
            :to="{ path: '/analyses', query: { task: analysis.id } }"
            class="sym-analysis-row"
            :aria-label="`Ouvrir l’analyse ${analysis.name}`"
            ><div
              class="sym-photo sym-analysis-photo"
              :class="
                analysis.thumbnail
                  ? `sym-photo-${analysis.thumbnail}`
                  : 'sym-thumbnail-empty'
              "
            >
              <VideoThumbnail
                v-if="analysis.source || analysis.poster"
                class="sym-real-thumbnail"
                :source="analysis.source"
                :poster="analysis.poster"
                :label="`Miniature de ${analysis.name}`"
              />
              <span class="sym-play" aria-hidden="true"
                ><svg viewBox="0 0 16 16"><path d="m6 3 7 5-7 5Z" /></svg
              ></span>
            </div>
            <div class="sym-analysis-name">
              <h3>{{ analysis.name }}</h3>
              <p>Analysée le {{ analysis.date }}</p>
            </div>
            <StatusBadge
              placement="inline"
              :status="analysis.validated ? 'validated' : 'pending'"
              :label="analysis.status" /><span class="sym-analysis-species"
              ><SymIcon name="paw" :size="23" />{{
                analysis.species ?? "—"
              }}
              espèce{{ analysis.species === 1 ? "" : "s" }}</span
            ><span class="sym-analysis-observations"
              ><SymIcon name="camera" :size="23" />{{
                analysis.observations ?? "—"
              }}
              observation{{ analysis.observations === 1 ? "" : "s" }}</span
            ><SymIcon name="chevron" :size="22"
          /></RouterLink>
        </li></ul
    ></GlassPanel>
  </div>
</template>
