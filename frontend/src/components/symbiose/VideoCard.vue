<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import type { Video } from "../../data/contracts";
import GlassPanel from "./GlassPanel.vue";
import SymIcon from "./SymIcon.vue";
import StatusBadge from "./StatusBadge.vue";
const props = defineProps<{ video: Video; selected: boolean }>();
const emit = defineEmits<{
  toggle: [id: string];
  preview: [video: Video];
  details: [video: Video];
}>();
const menuOpen = ref(false),
  root = ref<HTMLElement>(),
  menuButton = ref<HTMLButtonElement>();
async function toggleMenu() {
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value) {
    await nextTick();
    root.value?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
  }
}
function closeMenu(restore = false) {
  menuOpen.value = false;
  if (restore) menuButton.value?.focus();
}
function outside(event: PointerEvent) {
  if (root.value && !root.value.contains(event.target as Node)) closeMenu();
}
function menuKey(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.stopPropagation();
    closeMenu(true);
  }
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
  event.preventDefault();
  const buttons = Array.from(
    root.value?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') || [],
  );
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
  buttons[
    (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
      buttons.length
  ]?.focus();
}
function action(kind: "preview" | "details" | "toggle") {
  closeMenu();
  if (kind === "toggle") emit("toggle", props.video.id);
  else if (kind === "preview") emit("preview", props.video);
  else emit("details", props.video);
}
onMounted(() => document.addEventListener("pointerdown", outside));
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside));
</script>
<template>
  <article ref="root" class="sv-video-wrapper">
    <GlassPanel
      depth="card"
      as="div"
      class="sv-video-card"
      :class="{ 'is-selected': selected }"
      ><div
        class="sym-photo sv-thumbnail"
        :class="
          video.thumbnail
            ? `sv-photo-${video.thumbnail}`
            : 'sym-thumbnail-empty'
        "
      >
        <button
          class="sv-play-button"
          :aria-label="`Prévisualiser ${video.filename}`"
          @click="emit('preview', video)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m8 4 12 8-12 8Z" />
          </svg></button
        ><label class="sv-card-checkbox"
          ><span class="sym-sr-only">Sélectionner {{ video.filename }}</span
          ><input
            type="checkbox"
            :checked="selected"
            @change="emit('toggle', video.id)" /></label
        ><span class="sv-duration"
          ><SymIcon name="video" :size="13" />{{ video.duration || "—" }}</span
        >
      </div>
      <div class="sv-video-info">
        <div class="sv-video-title">
          <h3>{{ video.filename }}</h3>
          <button
            ref="menuButton"
            class="sv-more"
            :aria-label="`Actions pour ${video.filename}`"
            aria-haspopup="menu"
            :aria-expanded="menuOpen"
            @click="toggleMenu"
            @keydown.esc.stop="closeMenu(true)"
          >
            <SymIcon name="more" :size="24" />
          </button>
        </div>
        <p class="sv-video-parcel">
          <SymIcon name="pin" :size="14" />{{ video.parcel || "Non renseigné" }}
        </p>
        <p class="sv-video-date">
          <SymIcon name="calendar" :size="14" />{{ video.date || "—" }}
        </p>
        <StatusBadge :status="video.status" /></div
    ></GlassPanel>
    <div
      v-if="menuOpen"
      class="sv-card-menu"
      role="menu"
      :aria-label="`Actions pour ${video.filename}`"
      @keydown="menuKey"
    >
      <button role="menuitem" @click="action('preview')">Prévisualiser</button
      ><button role="menuitem" @click="action('details')">
        Voir les informations</button
      ><button role="menuitem" @click="action('toggle')">
        {{ selected ? "Désélectionner" : "Sélectionner" }} la vidéo
      </button>
    </div>
  </article>
</template>
