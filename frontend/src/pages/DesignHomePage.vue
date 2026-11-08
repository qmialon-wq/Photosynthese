<script setup lang="ts">
import {
  overview,
  journey,
  indicators,
  latestAnalyses,
} from "../data/home-preview";
import StatCard from "../components/symbiose/StatCard.vue";
import GlassPanel from "../components/symbiose/GlassPanel.vue";
import PillButton from "../components/symbiose/PillButton.vue";
import SymIcon from "../components/symbiose/SymIcon.vue";
</script>
<template>
  <div class="sym-home">
    <h1 class="sym-sr-only">Accueil Symbiose</h1>
    <div class="sym-overview" aria-label="Indicateurs de démonstration">
      <StatCard v-for="stat in overview" :key="stat.label" v-bind="stat" />
    </div>
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
      <GlassPanel class="sym-diagnostic" aria-labelledby="diagnostic-heading">
        <h2 id="diagnostic-heading" class="sym-panel-title">
          <span><SymIcon name="leaf" :size="25" /></span>Diagnostic écologique
        </h2>
        <div class="sym-diagnostic-body">
          <div
            class="sym-gauge"
            role="img"
            aria-label="État écologique de démonstration : 78 sur 100"
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
                  <stop stop-color="#9ff63b" />
                  <stop offset=".65" stop-color="#bafa77" />
                  <stop offset="1" stop-color="#d6ffd2" />
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
                stroke-dasharray="78 100"
              />
            </svg>
            <div>
              <strong>78</strong><span>/100</span>
              <p>État écologique</p>
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
          prioritaire
        </h2>
        <div class="sym-recommendation-body">
          <div
            class="sym-photo sym-photo-hedgerow"
            role="img"
            aria-label="Haies et prairie normandes"
          />
          <div>
            <h3>Maintenir et renforcer les haies</h3>
            <p>
              Favorise le déplacement de la faune et améliore la connectivité
              des habitats.
            </p>
          </div>
          <RouterLink
            to="/parcelles"
            class="sym-recommendation-next"
            aria-label="Consulter la recommandation sur les haies"
            ><SymIcon name="arrow" :size="23"
          /></RouterLink>
        </div>
        <div class="sym-carousel-dots" aria-hidden="true">
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
      <ul class="sym-analysis-list">
        <li v-for="analysis in latestAnalyses" :key="analysis.name">
          <RouterLink
            to="/analyses"
            class="sym-analysis-row"
            :aria-label="`Ouvrir l’analyse ${analysis.name}`"
            ><div
              class="sym-photo sym-analysis-photo"
              :class="`sym-photo-${analysis.thumbnail}`"
            >
              <span class="sym-play" aria-hidden="true"
                ><svg viewBox="0 0 16 16"><path d="m6 3 7 5-7 5Z" /></svg
              ></span>
            </div>
            <div class="sym-analysis-name">
              <h3>{{ analysis.name }}</h3>
              <p>Analysée le {{ analysis.date }}</p>
            </div>
            <span
              class="sym-status"
              :class="{ 'is-pending': !analysis.validated }"
              ><SymIcon
                :name="analysis.validated ? 'check' : 'hourglass'"
                :size="16"
              />{{ analysis.status }}</span
            ><span class="sym-analysis-species"
              ><SymIcon name="paw" :size="23" />{{
                analysis.species
              }}
              espèces</span
            ><span class="sym-analysis-observations"
              ><SymIcon name="camera" :size="23" />{{
                analysis.observations
              }}
              observations</span
            ><SymIcon name="chevron" :size="22"
          /></RouterLink>
        </li></ul
    ></GlassPanel>
  </div>
</template>
