<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { navigation } from "./router";
import { reviewer, saveReviewer } from "./api";
const route = useRoute();
const open = ref(false);
const sidebar = ref<HTMLElement | null>(null);
const menu = ref<HTMLButtonElement | null>(null);
watch(open, async (visible) => {
  await nextTick();
  if (visible)
    sidebar.value?.querySelector<HTMLAnchorElement>("nav a")?.focus();
  else if (window.matchMedia("(max-width:800px)").matches) menu.value?.focus();
});
const identity = ref(reviewer());
watch(identity, saveReviewer);
watch(
  () => route.path,
  () => {
    open.value = false;
  },
);
const title = computed(
  () =>
    navigation.find((item) => item.path === route.path)?.label ??
    "BioSentinelle",
);
</script>
<template>
  <a href="#main-content" class="skip-link">Aller au contenu</a>
  <div class="app-shell">
    <aside
      ref="sidebar"
      id="primary-navigation"
      class="sidebar"
      :class="{ 'is-open': open }"
      @keydown.esc="open = false"
    >
      <RouterLink to="/" class="brand" aria-label="BioSentinelle — accueil"
        ><span class="brand-mark"
          ><i class="pi pi-globe" aria-hidden="true" /></span
        ><span>BioSentinelle<small>NORMANDIE</small></span></RouterLink
      >
      <span class="nav-label">ESPACE D’OBSERVATION</span>
      <nav aria-label="Navigation principale">
        <RouterLink
          v-for="item in navigation"
          :key="item.path"
          :to="item.path"
          :class="{ selected: route.path === item.path }"
          :aria-current="route.path === item.path ? 'page' : undefined"
          ><i :class="['pi', item.icon]" aria-hidden="true" />{{
            item.label
          }}</RouterLink
        >
      </nav>
      <div class="sidebar-footer">
        <span class="local-dot" /> Plateforme locale<small
          >Vos données restent sur cette machine.</small
        >
      </div>
    </aside>
    <button
      v-if="open"
      class="nav-scrim"
      aria-label="Fermer le menu"
      @click="open = false"
    />
    <div class="workspace">
      <header class="topbar">
        <button
          class="menu-toggle"
          ref="menu"
          aria-controls="primary-navigation"
          aria-label="Menu de navigation"
          :aria-expanded="open"
          @click="open = !open"
        >
          <i class="pi pi-bars" /></button
        ><span class="breadcrumb"
          >Observatoire <span>/</span> <strong>{{ title }}</strong></span
        ><label class="reviewer"
          ><i class="pi pi-user" aria-hidden="true" /><span class="sr-only"
            >Nom de revue</span
          ><PInputText
            v-model="identity"
            aria-label="Nom de revue"
            placeholder="Votre nom de revue"
            size="small"
            maxlength="128"
        /></label>
      </header>
      <main id="main-content" tabindex="-1"><RouterView /></main>
      <footer class="app-footer">
        BioSentinelle Normandie
        <span>Observation · Validation · Connaissance</span>
      </footer>
    </div>
  </div>
</template>
