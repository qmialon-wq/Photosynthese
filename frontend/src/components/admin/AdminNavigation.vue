<script setup lang="ts">
import { adminSections, lastObservationRoute } from "../../admin/navigation";
import SymIcon from "../symbiose/SymIcon.vue";
defineEmits<{ navigate: [] }>();
</script>
<template>
  <nav aria-label="Navigation administrative">
    <RouterLink
      v-for="section in adminSections"
      :key="section.path"
      :to="section.path"
      :class="{ 'is-active': $route.path === section.path }"
      :aria-current="$route.path === section.path ? 'page' : undefined"
      @click="$emit('navigate')"
    >
      <SymIcon :name="section.icon" :size="21" /><span>{{
        section.label
      }}</span>
    </RouterLink>
    <RouterLink
      class="adm-return"
      :to="lastObservationRoute"
      @click="$emit('navigate')"
      ><SymIcon name="arrow" :size="20" />Retour à l’espace
      observation</RouterLink
    >
    <RouterLink to="/profil" @click="$emit('navigate')"
      ><SymIcon name="user" :size="20" />Mon profil</RouterLink
    >
  </nav>
</template>
