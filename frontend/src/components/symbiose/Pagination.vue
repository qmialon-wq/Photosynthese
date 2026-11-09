<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(
  defineProps<{
    page: number;
    total: number;
    pageSize: number;
    itemLabel?: string;
    navigationLabel?: string;
    variant?: "numbered" | "simple";
  }>(),
  {
    itemLabel: "vidéo",
    navigationLabel: "Pagination des vidéos",
    variant: "numbered",
  },
);
const emit = defineEmits<{ change: [page: number] }>();
const pageCount = computed(() =>
  Math.max(1, Math.ceil(props.total / props.pageSize)),
);
const start = computed(() =>
  props.total ? (props.page - 1) * props.pageSize + 1 : 0,
);
const end = computed(() => Math.min(props.total, props.page * props.pageSize));
const buttons = computed(() => {
  const last = pageCount.value;
  if (last <= 7) return Array.from({ length: last }, (_, i) => i + 1);
  const center = Math.min(Math.max(props.page - 1, 1), last - 2);
  const pages = [...new Set([1, center, center + 1, center + 2, last])].sort(
    (a, b) => a - b,
  );
  const result: (number | string)[] = [];
  pages.forEach((page, i) => {
    const previous = pages[i - 1];
    if (previous && page - previous === 2) result.push(page - 1);
    else if (previous && page - previous > 2) result.push(`gap-${previous}`);
    result.push(page);
  });
  return result;
});
</script>
<template>
  <div class="sv-pagination">
    <p v-if="variant === 'numbered'" role="status">
      {{ start }} – {{ end }} sur {{ total }} {{ itemLabel
      }}{{ total === 1 ? "" : "s" }}
    </p>
    <nav :aria-label="navigationLabel">
      <button
        class="sv-page-step"
        :disabled="page <= 1"
        @click="emit('change', page - 1)"
      >
        {{ variant === "simple" ? "Page précédente" : "Précédent" }}</button
      ><span v-if="variant === 'simple'" class="sv-page-current" role="status"
        >Page {{ page }}</span
      ><template
        v-for="button in variant === 'numbered' ? buttons : []"
        :key="button"
        ><button
          v-if="typeof button === 'number'"
          class="sv-page-number"
          :class="{ 'is-current': page === button }"
          :aria-label="`Page ${button}`"
          :aria-current="page === button ? 'page' : undefined"
          @click="emit('change', button)"
        >
          {{ button }}</button
        ><span v-else class="sv-page-gap" aria-hidden="true">…</span></template
      ><button
        class="sv-page-step"
        :disabled="page >= pageCount"
        @click="emit('change', page + 1)"
      >
        {{ variant === "simple" ? "Page suivante" : "Suivant" }}
      </button>
    </nav>
  </div>
</template>
