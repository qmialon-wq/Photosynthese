<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  symbioseNavigation,
  wheelSlot,
  ACTIVE_WHEEL_SLOT,
} from "../../symbiose-navigation";
import {
  createWheelMotion,
  nearestWheelTarget,
  sampleWheelMotion,
  wheelPose,
} from "./wheel-motion";
import SymIcon from "./SymIcon.vue";

const props = defineProps<{ reducedMotion?: boolean }>();
const route = useRoute();
const wheel = ref<HTMLElement>();
const links = ref<HTMLAnchorElement[]>([]);
const phase = ref<"idle" | "rotating" | "locking">("idle");
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
const systemReducedMotion = ref(motionPreference.matches);
const reducedMotion = computed(
  () => props.reducedMotion || systemReducedMotion.value,
);
const activeIndex = computed(() =>
  Math.max(
    0,
    symbioseNavigation.findIndex(
      (item) =>
        item.path === route.path ||
        (item.path !== "/" && route.path.startsWith(`${item.path}/`)),
    ),
  ),
);
const items = computed(() =>
  symbioseNavigation.map((item, index) => ({
    ...item,
    index,
    slot: wheelSlot(index, activeIndex.value),
  })),
);

// Une seule horloge et une seule progression pour les six liens.
// Les dimensions sont mises en cache par ResizeObserver, jamais lues par frame.
let progression = activeIndex.value;
let velocity = 0;
let width = 300;
let height = 852;
let frame = 0;
let started = 0;
let lockStarted: number | undefined;
let motion: ReturnType<typeof createWheelMotion> | undefined;
let observer: ResizeObserver | undefined;

function paint(lock = 0) {
  wheel.value?.style.setProperty("--wheel-lock", String(lock));
  for (let index = 0; index < symbioseNavigation.length; index++) {
    const link = links.value[index];
    if (!link) continue;
    const pose = wheelPose(index, progression);
    link.style.transform = `translate3d(${(pose.x / 300) * width}px, ${(pose.y / 852) * height}px, 0) translate(-50%, -50%)`;
    link.style.opacity = String(pose.opacity);
    link.style.setProperty("--wheel-engagement", String(pose.engagement));
    link.style.setProperty(
      "--wheel-label-opacity",
      String(Math.max(0, (pose.engagement - 0.35) / 0.65)),
    );
    // Le raccord invisible ne doit pas intercepter un clic sur le contenu.
    link.style.pointerEvents = pose.opacity < 0.08 ? "none" : "";
  }
}

function stop() {
  cancelAnimationFrame(frame);
  frame = 0;
  motion = undefined;
  lockStarted = undefined;
  velocity = 0;
}
function settleImmediately() {
  stop();
  progression = activeIndex.value;
  phase.value = "idle";
  paint();
}
function tick(now: number) {
  frame = 0;
  if (motion) {
    const sample = sampleWheelMotion(motion, now - started);
    progression = sample.position;
    velocity = sample.velocity;
    if (sample.done) {
      motion = undefined;
      lockStarted = now;
      phase.value = "locking";
    }
  }
  const lockElapsed = lockStarted === undefined ? undefined : now - lockStarted;
  // Confirmation lumineuse de 170 ms, après le retour exact au cran.
  const lock =
    lockElapsed === undefined
      ? 0
      : Math.sin(Math.PI * Math.min(1, lockElapsed / 170)) * 0.7;
  paint(lock);
  if (motion || (lockElapsed !== undefined && lockElapsed < 170)) {
    frame = requestAnimationFrame(tick);
  } else {
    lockStarted = undefined;
    phase.value = "idle";
    paint();
  }
}
function rotateToSelection() {
  if (reducedMotion.value) return settleImmediately();
  cancelAnimationFrame(frame);
  const target = nearestWheelTarget(progression, activeIndex.value);
  motion = createWheelMotion(progression, velocity, target);
  lockStarted = undefined;
  started = performance.now();
  phase.value = "rotating";
  frame = requestAnimationFrame(tick);
}
function updateMotionPreference(event: MediaQueryListEvent) {
  systemReducedMotion.value = event.matches;
}
function measureLabels() {
  // Composition naturelle identique au bouton d'origine, mesurée seulement
  // au montage, au chargement des polices et au changement de breakpoint.
  const widths = links.value.map(
    (link) =>
      link.querySelector(".sym-wheel-label")?.getBoundingClientRect().width ??
      0,
  );
  links.value.forEach((link, index) =>
    link.style.setProperty("--wheel-label-width", `${widths[index]}px`),
  );
}
watch(activeIndex, rotateToSelection, { flush: "post" });
watch(
  reducedMotion,
  (reduced) => {
    if (reduced) settleImmediately();
  },
  { flush: "post" },
);
onMounted(() => {
  motionPreference.addEventListener("change", updateMotionPreference);
  observer = new ResizeObserver(([entry]) => {
    width = entry.contentRect.width;
    height = entry.contentRect.height;
    measureLabels();
    paint();
  });
  if (wheel.value) {
    width = wheel.value.clientWidth;
    height = wheel.value.clientHeight;
    observer.observe(wheel.value);
  }
  measureLabels();
  void document.fonts.ready.then(() => {
    if (wheel.value) measureLabels();
  });
  paint();
});
onBeforeUnmount(() => {
  stop();
  observer?.disconnect();
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
  <nav
    ref="wheel"
    class="sym-wheel"
    :data-motion="phase"
    aria-label="Navigation principale"
  >
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
          <stop stop-color="var(--sym-shade-accent-e4f5cc)" stop-opacity="0" />
          <stop offset=".28" stop-color="var(--sym-shade-accent-e8f5da)" stop-opacity=".9" />
          <stop offset=".65" stop-color="var(--sym-shade-accent-e8f5da)" />
          <stop offset="1" stop-color="var(--sym-shade-accent-e4f5cc)" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M298 190C130 315 135 548 298 710"
        stroke="url(#wheel-arc-light)"
        stroke-width="1.5"
      />
    </svg>
    <span class="sym-wheel-detent" aria-hidden="true" />
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
