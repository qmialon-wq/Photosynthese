<script setup lang="ts">
import { computed } from "vue";
import { citationParts, type ArticleIndex } from "../source-links";
const props = defineProps<{ text: string; sources: ArticleIndex }>();
const parts = computed(() => citationParts(props.text, props.sources));
</script>

<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><a
        v-if="part.href"
        :href="part.href"
        target="_blank"
        rel="noopener noreferrer"
        >{{ part.text }}</a
      ><template v-else>{{ part.text }}</template></template
    ></span
  >
</template>
