<script setup lang="ts">
import { ref } from "vue";
import { sources, producers } from "./sources";
import {
  pitchChapters,
  juryCoverage,
  clock,
  statusLabels,
  pitchWordCount,
} from "./pitch";
const props = defineProps<{ chapterId: string }>();
const tab = ref<"sources" | "speaker" | "jury">("sources");
</script>
<template>
  <div class="sx-source-book">
    <p class="sx-eyebrow">CARNET DE PRÉSENTATION</p>
    <h2 id="sx-project-title">
      Les preuves, les mots,<br /><em>les prochaines étapes.</em>
    </h2>
    <div class="sx-book-tabs" role="group" aria-label="Contenu du carnet">
      <button :aria-pressed="tab === 'sources'" @click="tab = 'sources'">
        Sources et technique
      </button>
      <button :aria-pressed="tab === 'speaker'" @click="tab = 'speaker'">
        Pitch chronométré
      </button>
      <button :aria-pressed="tab === 'jury'" @click="tab = 'jury'">
        Attendus du jury
      </button>
    </div>
    <template v-if="tab === 'sources'">
      <p>
        Le manifeste, ses captures et les livrables du dépôt étayent ce
        parcours. Les textes ci-dessous sont embarqués localement et restent
        consultables sans Internet.
      </p>
      <p class="sx-source-limit">
        <strong>Attendus vérifiés :</strong> les cinq questions de l’image
        fournie, les sept rubriques du descriptif et les six critères du
        règlement (§ 5, p. 3). La vidéo produit sera réalisée ultérieurement par
        l’équipe ; elle reste à ajouter au lecteur.
      </p>
      <dl class="sx-evidence-key">
        <div>
          <dt>Fonction documentée</dt>
          <dd>
            Capacité décrite dans les livrables ; configuration locale requise
            pour l’exécuter.
          </dd>
        </div>
        <div>
          <dt>Résultat technique vérifié</dt>
          <dd>
            Recette ou archive datée ; aucune efficacité écologique déduite.
          </dd>
        </div>
        <div>
          <dt>Bénéfice attendu</dt>
          <dd>
            Utilité visée ; aucun gain de temps ou de biodiversité mesuré.
          </dd>
        </div>
        <div>
          <dt>Perspective</dt>
          <dd>Développement ou évaluation à venir.</dd>
        </div>
      </dl>
      <h3>Documents examinés</h3>
      <details
        v-for="source in sources"
        :key="source.id"
        :open="
          pitchChapters
            .find((c) => c.id === props.chapterId)
            ?.sources.includes(source.id) || undefined
        "
      >
        <summary>{{ source.title }}</summary>
        <p>{{ source.scope }}</p>
        <small>{{ source.path }}</small>
        <details class="sx-source-original">
          <summary>Lire le texte local du document</summary>
          <pre>{{ source.text }}</pre>
        </details>
      </details>
      <h3>Producteurs des données utilisées</h3>
      <p>
        Ces liens externes sont facultatifs et nécessitent Internet. La scène ne
        consulte aucun service distant.
      </p>
      <ul>
        <li v-for="[label, url] in producers" :key="url">
          <a :href="url" target="_blank" rel="noopener noreferrer"
            >{{ label }} ↗</a
          >
        </li>
      </ul>
      <h3>Faisabilité et numérique responsable</h3>
      <p>
        FastAPI et Vue 3, workers vision et documentaire séparés, PostgreSQL et
        Redis, stockage local persistant. La détection, la classification et le
        suivi restent distincts. Les tâches longues passent par une file ; une
        seule tâche GPU lourde s’exécute à la fois. Les modèles se préparent
        explicitement.
      </p>
      <p>
        Les traitements locaux et l’absence d’entraînement automatique sont des
        choix d’architecture. La consommation énergétique, le gain de temps et
        l’impact écologique restent à mesurer.
      </p>
      <p>
        Le RPG décrit une occupation agricole déclarée pour 2024. Un point et un
        zonage n’établissent ni l’état de toute une parcelle ni l’efficacité
        d’une adaptation. Les suggestions et publications doivent être examinées
        avant décision ; la compensation reste non évaluée.
      </p>
    </template>
    <template v-else-if="tab === 'speaker'">
      <p>
        Cinq minutes, dont 90 secondes de démonstration. Environ
        {{ pitchWordCount }} mots hors vidéo. Le compteur de l’expérience
        indique la position dans le script ; une répétition chronométrée reste
        nécessaire.
      </p>
      <section
        v-for="chapter in pitchChapters"
        :key="chapter.id"
        class="sx-speaker-chapter"
      >
        <p class="sx-eyebrow">
          {{ clock(chapter.start) }}–{{
            clock(chapter.start + chapter.duration)
          }}
          · {{ chapter.duration }} S
        </p>
        <h3>{{ chapter.subject }}</h3>
        <p>
          <strong>{{ chapter.message }}</strong>
        </p>
        <p class="sx-script">{{ chapter.oral }}</p>
        <small>{{ statusLabels[chapter.status] }}</small>
        <details>
          <summary>À l’écran et transition</summary>
          <p>{{ chapter.screen.join(" · ") }}</p>
          <p>{{ chapter.interaction }}</p>
          <p>{{ chapter.transition }}</p>
        </details>
      </section>
    </template>
    <template v-else>
      <p>
        Correspondance avec les cinq questions fournies et les six critères du
        règlement (§ 5, p. 3), complétée par l’Open Data et l’ancrage normand.
        Les rôles individuels et les moyens financiers ne sont pas documentés.
      </p>
      <div
        class="sx-table-scroll"
        tabindex="0"
        role="region"
        aria-label="Correspondance jury et scènes"
      >
        <table>
          <caption>
            Attendus et scènes du pitch
          </caption>
          <thead>
            <tr>
              <th scope="col">Attendu</th>
              <th scope="col">Scènes</th>
              <th scope="col">Éléments présentés</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in juryCoverage" :key="row[0]">
              <th scope="row">{{ row[0] }}</th>
              <td>{{ row[1] }}</td>
              <td>{{ row[2] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
