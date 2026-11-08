<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import type { DemoProject } from "../../data/project-preview";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
import StatusBadge from "./StatusBadge.vue";
defineProps<{ project: DemoProject }>();
const emit = defineEmits<{ open: [project: DemoProject] }>();
const router = useRouter();
const menu = ref<HTMLDetailsElement>(),
  openButton = ref<HTMLButtonElement>(),
  summary = ref<HTMLElement>();
const expanded = ref(false);
async function menuToggled() {
  expanded.value = !!menu.value?.open;
  if (menu.value?.open) {
    await nextTick();
    menu.value.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
  }
}
function closeMenu() {
  if (menu.value) menu.value.open = false;
}
function outside(event: PointerEvent) {
  if (!menu.value?.contains(event.target as Node)) closeMenu();
}
function openProject(project: DemoProject) {
  closeMenu();
  openButton.value?.focus();
  emit("open", project);
}
function menuKey(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    closeMenu();
    summary.value?.focus();
  }
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
  event.preventDefault();
  const buttons = Array.from(
    menu.value?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') || [],
  );
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
  buttons[
    (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
      buttons.length
  ]?.focus();
}
onMounted(() => document.addEventListener("pointerdown", outside));
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside));
</script>
<template>
  <GlassPanel as="article" class="sf-project-card">
    <button
      ref="openButton"
      class="sf-project-open"
      :aria-label="`Ouvrir le dossier ${project.name}`"
      @click="openProject(project)"
    >
      <div
        class="sf-project-photo"
        :class="`sf-landscape-${project.landscape}`"
      >
        <StatusBadge
          :status="project.status"
          :label="project.status === 'validated' ? 'Validé' : undefined"
        />
      </div>
      <div class="sf-project-info">
        <h2><SymIcon name="folder" :size="23" />{{ project.name }}</h2>
        <div class="sf-project-counts">
          <span
            ><SymIcon name="video" :size="21" />{{
              project.videos
            }}
            vidéos</span
          ><span
            ><SymIcon name="paw" :size="23" />{{
              project.species
            }}
            espèces</span
          >
        </div>
      </div>
    </button>
    <details
      ref="menu"
      class="sf-project-menu"
      @toggle="menuToggled"
      @keydown="menuKey"
    >
      <summary
        ref="summary"
        role="button"
        :aria-label="`Actions pour ${project.name}`"
        aria-haspopup="menu"
        :aria-expanded="expanded"
      >
        <SymIcon name="more" :size="25" />
      </summary>
      <div role="menu" :aria-label="`Actions pour ${project.name}`">
        <button role="menuitem" @click="openProject(project)">
          Ouvrir le dossier</button
        ><button role="menuitem" @click="openProject(project)">
          Voir les informations</button
        ><button
          role="menuitem"
          @click="
            closeMenu();
            router.push('/videos');
          "
        >
          Choisir des vidéos
        </button>
      </div>
    </details>
  </GlassPanel>
</template>
