<script setup lang="ts">
import { ref } from "vue";
import type { ChapterId } from "./config";
import evidence from "./content/territorial-evidence.json";
defineProps<{ chapter: ChapterId }>();
const emit = defineEmits<{ sources: [] }>();
const place = ref(1),
  step = ref(0);
const layers: Record<string, string> = {
  znieff1: "ZNIEFF I",
  znieff2: "ZNIEFF II",
  "natura-habitat": "Natura · Habitats",
  "natura-oiseaux": "Natura · Oiseaux",
};
const pipeline = [
  [
    "Vidéo",
    "Les vidéos sont importées dans le stockage local et associées au dossier.",
  ],
  [
    "Extraction",
    "Des images sont extraites pour permettre l’analyse visuelle.",
  ],
  [
    "Reconnaissance",
    "MegaDetector localise les animaux. Le classificateur PyTorch propose une espèce ; le suivi relie les observations dans le temps.",
  ],
  [
    "Validation",
    "Une personne confirme, corrige ou rejette l’espèce et le recadrage. Une prédiction seule ne confirme pas une présence.",
  ],
  [
    "Enrichissement",
    "Les observations confirmées sont rapprochées des données ouvertes et des publications, avec leur provenance.",
  ],
  [
    "Propositions",
    "Des alternatives conditionnelles sont reliées au projet, aux sources et aux vérifications encore nécessaires.",
  ],
];
</script>
<template>
  <div
    v-if="chapter === 'forest'"
    class="sx-field-glimpse"
    aria-label="Illustration d’une observation par caméra piège"
  >
    <svg viewBox="0 0 180 90" aria-hidden="true">
      <path
        d="M13 5v77m-9-42h30v22H4V40Zm16 11a6 6 0 1 0 .01 0M97 55l12-8 30 2 9-14 7 3-8 18-12 5-5 21m-24-24-5 24m8-35 1-12-8-9m8 9 9-10m29 11 3-12m-3 12 12-6"
      />
    </svg>
    <span>Caméra piège → observation à vérifier</span
    ><small>Illustration · espèce et confiance non calculées</small>
  </div>
  <div v-else-if="chapter === 'rivers'" class="sx-data-confluence">
    <div class="sx-tributaries" aria-label="Sources utilisées par le prototype">
      <span>Observations validées</span><span>Cadastre · RPG 2024</span
      ><span>IGN · DREAL Normandie</span><span>Publications scientifiques</span>
    </div>
    <svg
      class="sx-river-links"
      viewBox="0 0 600 55"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M70 0C70 40 300 15 300 55M220 0C220 20 300 20 300 55M380 0C380 20 300 20 300 55M530 0C530 40 300 15 300 55"
      />
    </svg>
    <details class="sx-archive">
      <summary>Résultats vérifiés · deux points normands</summary>
      <p class="sx-archive-tag">
        ARCHIVES IGN · 10 NOVEMBRE 2026 · AUCUN APPEL EN DIRECT
      </p>
      <div class="sx-place-choice" role="group" aria-label="Point archivé">
        <button
          v-for="(record, index) in evidence"
          :key="record.place"
          :aria-pressed="place === index"
          @click="place = index"
        >
          {{ record.place }}
        </button>
      </div>
      <p>
        {{ evidence[place].location.latitude }},
        {{ evidence[place].location.longitude }} · WGS84
      </p>
      <ul class="sx-layer-matrix">
        <li v-for="layer in evidence[place].layers" :key="layer.code">
          <span>{{ layers[layer.code] }}</span
          ><strong>{{
            layer.status === "empty"
              ? "Aucun objet renvoyé"
              : layer.features.map((f) => f.source_id).join(", ")
          }}</strong>
        </li>
      </ul>
      <p>
        Ces réponses concernent seulement le point interrogé. Une réponse vide
        ne prouve pas l’absence d’enjeu écologique.
      </p>
      <button class="sx-inline-source" @click="emit('sources')">
        Consulter les preuves et leurs limites ↗
      </button>
    </details>
  </div>
  <div v-else-if="chapter === 'underwater'" class="sx-future-signal">
    <i aria-hidden="true" /><span>Écoute et captation aquatiques</span
    ><strong>À développer · à valider</strong>
  </div>
  <div v-else-if="chapter === 'wetland'" class="sx-living-pipeline">
    <ol aria-label="Étapes de traitement">
      <li v-for="(item, index) in pipeline" :key="item[0]">
        <button :aria-pressed="step === index" @click="step = index">
          <span>0{{ index + 1 }}</span
          >{{ item[0] }}
        </button>
      </li>
    </ol>
    <p class="sx-pipeline-detail" aria-live="polite">{{ pipeline[step][1] }}</p>
    <small
      >Traitements locaux · tâches en arrière-plan · GPU partagé
      séquentiellement</small
    >
  </div>
  <div v-else-if="chapter === 'coast'" class="sx-impact-proof">
    <strong>12 <span>alternatives documentées</span></strong
    ><span
      >Clôture · éclairage · végétation · terrassement ·
      imperméabilisation</span
    ><button class="sx-inline-source" @click="emit('sources')">
      Inventaire du prototype et limites ↗</button
    ><small>Efficacité écologique locale : non mesurée</small>
  </div>
</template>
