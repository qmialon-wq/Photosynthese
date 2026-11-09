<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  symbioseNavigation,
  wheelSlot,
  wheelSlots,
  ACTIVE_WHEEL_SLOT,
} from "../../symbiose-navigation";
import SymIcon from "./SymIcon.vue";
const props = defineProps<{ reducedMotion?: boolean }>();
const route = useRoute();
const links = ref<HTMLAnchorElement[]>([]);
const animations = new Map<
  number,
  { animation: Animation; from: number; to: number }
>();
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
const systemReducedMotion = ref(motionPreference.matches);
const reducedMotion = computed(
  () => props.reducedMotion || systemReducedMotion.value,
);
function cancelAnimations() {
  animations.forEach(({ animation }) => animation.cancel());
  animations.clear();
}
function updateMotionPreference(event: MediaQueryListEvent) {
  systemReducedMotion.value = event.matches;
}
onMounted(() =>
  motionPreference.addEventListener("change", updateMotionPreference),
);
watch(reducedMotion, (reduced) => {
  if (reduced) cancelAnimations();
});
const activeIndex = computed(() =>
  Math.max(
    0,
    symbioseNavigation.findIndex((item) => item.path === route.path),
  ),
);
const items = computed(() =>
  symbioseNavigation.map((item, index) => {
    const slot = wheelSlot(index, activeIndex.value);
    return { ...item, index, slot, position: wheelSlots[slot] };
  }),
);
// Interpolation de la trajectoire : les liens suivent l’arc, sans rotation des SVG.
function pointAlongArc(position: number) {
  const segment = Math.min(4, Math.floor(position));
  const t = position - segment;
  const points = [-1, 0, 1, 2].map(
    (offset) => wheelSlots[Math.max(0, Math.min(5, segment + offset))],
  );
  const interpolate = (key: "x" | "y") => {
    const [a, b, c, d] = points.map((point) => point[key]);
    return (
      0.5 *
      (2 * b +
        (-a + c) * t +
        (2 * a - 5 * b + 4 * c - d) * t * t +
        (-a + 3 * b - 3 * c + d) * t * t * t)
    );
  };
  return { x: interpolate("x"), y: interpolate("y") };
}
watch(
  activeIndex,
  (active, previous) => {
    for (let index = 0; index < 6; index++) {
      const element = links.value[index];
      const interrupted = animations.get(index);
      // Repartir de la position interpolée, même lors de clics très rapprochés.
      const progress =
        interrupted?.animation.effect?.getComputedTiming().progress ?? 1;
      const from = interrupted
        ? interrupted.from + (interrupted.to - interrupted.from) * progress
        : wheelSlot(index, previous);
      const to = wheelSlot(index, active);
      const opacity = element ? getComputedStyle(element).opacity : "1";
      interrupted?.animation.cancel();
      animations.delete(index);
      if (reducedMotion.value || !element || from === to) continue;
      const frames = Array.from({ length: 31 }, (_, frame) => {
        const fraction = frame / 30;
        const point = pointAlongArc(from + (to - from) * fraction);
        return {
          left: `${point.x / 3}%`,
          top: `${(point.y / 852) * 100}%`,
          opacity: Number(opacity) + (1 - Number(opacity)) * fraction,
        };
      });
      const animation = element.animate(frames, {
        duration: 700,
        easing: "cubic-bezier(.22,.75,.22,1)",
      });
      animations.set(index, { animation, from, to });
      animation.onfinish = () => {
        if (animations.get(index)?.animation === animation)
          animations.delete(index);
      };
    }
  },
  { flush: "post" },
);
onBeforeUnmount(() => {
  cancelAnimations();
  motionPreference.removeEventListener("change", updateMotionPreference);
});
function focusAdjacent(event: KeyboardEvent, index: number) {
  const step =
    event.key === "ArrowDown" || event.key === "ArrowRight"
      ? 1
      : event.key === "ArrowUp" || event.key === "ArrowLeft"
        ? -1
        : 0;
  if (!step) return;
  event.preventDefault();
  links.value[(index + step + 6) % 6]?.focus();
}
</script>
<template>
  <nav class="sym-wheel" aria-label="Navigation principale">
    <svg
      class="sym-wheel-arc"
      viewBox="0 0 300 852"
      preserveAspectRatio="none"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id="wheel-arc-light"
          x1="265"
          y1="190"
          x2="265"
          y2="710"
          gradientUnits="userSpaceOnUse"
        >
          <stop stop-color="#e4f5cc" stop-opacity="0" />
          <stop offset=".28" stop-color="#e8f5da" stop-opacity=".9" />
          <stop offset=".65" stop-color="#e8f5da" />
          <stop offset="1" stop-color="#e4f5cc" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M298 190C130 315 135 548 298 710"
        stroke="url(#wheel-arc-light)"
        stroke-width="1.5"
      />
    </svg>
    <RouterLink
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      custom
      v-slot="{ href, navigate }"
      ><a
        :ref="
          (el) => {
            if (el) links[item.index] = el as HTMLAnchorElement;
          }
        "
        :href="href"
        class="sym-wheel-link"
        :class="{
          'is-active': item.slot === ACTIVE_WHEEL_SLOT,
          'has-long-label': item.label.length > 12,
          'has-compact-label': item.label.length > 8 && item.label.length <= 12,
        }"
        :style="{
          left: `${item.position.x / 3}%`,
          top: `${(item.position.y / 852) * 100}%`,
        }"
        :data-slot="item.slot + 1"
        :data-section="item.path"
        :aria-label="item.label"
        :aria-current="item.slot === ACTIVE_WHEEL_SLOT ? 'page' : undefined"
        @click="navigate"
        @keydown="focusAdjacent($event, item.index)"
        ><SymIcon :name="item.icon" :size="29" /><span
          class="sym-wheel-label"
          >{{ item.label }}</span
        ><span class="sym-wheel-tooltip" aria-hidden="true">{{
          item.label
        }}</span></a
      ></RouterLink
    >
  </nav>
</template>
