<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { auth } from "../auth-state";
import {
  clientGuide,
  openClientGuide,
  guideStep,
  dismissClientGuide,
  resetClientGuide,
  shouldShowClientGuide,
} from "../client-guide";
import { clientGuideCards } from "../data/client-guide";
import { useLoginTransition } from "../composables/useLoginTransition";
import SymIcon from "./symbiose/SymIcon.vue";
import "../styles/client-guide.css";

const route = useRoute(),
  router = useRouter();
const transition = useLoginTransition();
const dialog = ref<HTMLDialogElement>(),
  title = ref<HTMLElement>();
const zoomed = ref(false);
const card = computed(() => clientGuideCards[clientGuide.step.value]);
const screenshots = import.meta.glob<string>("../assets/guide/*.png", {
  eager: true,
  query: "?url",
  import: "default",
});
const screenshot = computed(
  () => screenshots[`../assets/guide/${card.value.image}.png`],
);
const workspace = computed(
  () =>
    !!auth.user &&
    route.matched.length > 0 &&
    (!route.meta.public || route.meta.home),
);
watch(
  () => auth.user?.id,
  () => resetClientGuide(),
  { flush: "sync" },
);
watch(
  [
    () => auth.user?.client_guide_seen_at,
    () => auth.user?.id,
    workspace,
    () => transition.active.value,
  ],
  () => {
    if (workspace.value && !transition.active.value && shouldShowClientGuide())
      openClientGuide();
  },
  { immediate: true },
);
watch(
  clientGuide.open,
  async (open) => {
    if (open) zoomed.value = false;
    await nextTick();
    if (open && !dialog.value?.open) {
      dialog.value?.showModal();
      title.value?.focus();
    }
    if (!open && dialog.value?.open) dialog.value.close();
  },
  { immediate: true },
);
watch(clientGuide.step, async () => {
  zoomed.value = false;
  await nextTick();
  title.value?.focus();
});
watch(zoomed, async (value) => {
  await nextTick();
  if (value)
    dialog.value
      ?.querySelector<HTMLElement>(".client-guide-image-scroll")
      ?.focus();
  else title.value?.focus();
});
function move(direction: number) {
  if (zoomed.value) return;
  guideStep(
    Math.max(
      0,
      Math.min(clientGuideCards.length - 1, clientGuide.step.value + direction),
    ),
  );
}
function key(event: KeyboardEvent) {
  if (zoomed.value) return;
  if (event.key === "ArrowRight") {
    event.preventDefault();
    move(1);
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    move(-1);
  }
}
async function start() {
  void dismissClientGuide();
  await router.push(auth.user ? "/videos" : "/connexion");
}
onBeforeUnmount(() => dialog.value?.close());
</script>

<template>
  <dialog
    ref="dialog"
    id="client-guide"
    class="client-guide"
    aria-labelledby="client-guide-title"
    aria-describedby="client-guide-duration"
    @cancel.prevent="zoomed ? (zoomed = false) : dismissClientGuide()"
    @keydown="key"
  >
    <header class="client-guide-header">
      <span class="client-guide-brand"
        ><SymIcon name="leaf" :size="22" />Votre guide Symbiose</span
      >
      <span id="client-guide-duration"
        >2–3 min · {{ clientGuide.step.value + 1 }} /
        {{ clientGuideCards.length }}</span
      >
      <button
        class="client-guide-close"
        aria-label="Fermer le guide"
        @click="dismissClientGuide"
      >
        <SymIcon name="close" :size="22" />
      </button>
    </header>
    <div
      v-if="clientGuide.open.value && !zoomed"
      :key="clientGuide.step.value"
      class="client-guide-card"
    >
      <section class="client-guide-copy">
        <p class="client-guide-eyebrow">{{ card.eyebrow }}</p>
        <h2 id="client-guide-title" ref="title" tabindex="-1">
          {{ card.title }}
        </h2>
        <p class="client-guide-intro">{{ card.intro }}</p>
        <ul>
          <li v-for="bullet in card.bullets" :key="bullet">{{ bullet }}</li>
        </ul>
      </section>
      <figure v-if="screenshot" class="client-guide-figure">
        <button
          class="client-guide-image-button"
          aria-label="Agrandir la capture d’écran"
          @click="zoomed = true"
        >
          <img :src="screenshot" :alt="card.alt" width="1120" height="760" />
          <span
            v-for="(mark, index) in card.marks"
            :key="mark.label"
            class="client-guide-pin"
            :style="{ left: `${mark.x}%`, top: `${mark.y}%` }"
            aria-hidden="true"
            >{{ index + 1 }}</span
          >
          <span class="client-guide-zoom"
            ><SymIcon name="fullscreen" :size="16" />Agrandir</span
          >
        </button>
        <figcaption>
          <span v-for="(mark, index) in card.marks" :key="mark.label"
            ><b>{{ index + 1 }}</b
            >{{ mark.label }}</span
          ><small>Capture de l’interface · données d’exemple</small>
        </figcaption>
      </figure>
    </div>
    <section v-else-if="clientGuide.open.value" class="client-guide-enlarged">
      <h2 id="client-guide-title">{{ card.title }} — capture agrandie</h2>
      <button class="client-guide-secondary" @click="zoomed = false">
        Revenir à la carte
      </button>
      <div
        class="client-guide-image-scroll"
        tabindex="0"
        role="region"
        aria-label="Capture agrandie, faites défiler pour explorer les détails"
      >
        <img :src="screenshot" :alt="card.alt" />
      </div>
      <p>Faites défiler l’image pour explorer les détails.</p>
      <p>Capture de l’interface · données d’exemple</p>
    </section>
    <p v-if="clientGuide.error.value" class="client-guide-error" role="status">
      {{ clientGuide.error.value }}
    </p>
    <footer
      v-if="clientGuide.open.value && !zoomed"
      class="client-guide-footer"
    >
      <button class="client-guide-secondary" @click="dismissClientGuide">
        {{
          clientGuide.step.value === clientGuideCards.length - 1
            ? "Terminer le guide"
            : "Plus tard"
        }}
      </button>
      <nav aria-label="Étapes du guide">
        <button
          v-for="(item, index) in clientGuideCards"
          :key="item.title"
          :aria-label="`Étape ${index + 1} : ${item.title}`"
          :aria-current="clientGuide.step.value === index ? 'step' : undefined"
          @click="guideStep(index)"
        >
          <span />
        </button>
      </nav>
      <div class="client-guide-navigation">
        <button
          class="client-guide-secondary"
          :disabled="clientGuide.step.value === 0"
          @click="move(-1)"
        >
          Précédent</button
        ><button
          v-if="clientGuide.step.value < clientGuideCards.length - 1"
          class="client-guide-primary"
          @click="move(1)"
        >
          Suivant <SymIcon name="arrow" :size="18" /></button
        ><button v-else class="client-guide-primary" @click="start">
          {{
            auth.user
              ? "Importer mes premières vidéos"
              : "Se connecter pour commencer"
          }}
        </button>
      </div>
    </footer>
  </dialog>
</template>
