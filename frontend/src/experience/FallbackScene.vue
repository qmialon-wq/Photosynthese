<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { transitionAt, reducedProgress } from "./journey";
import { sceneAsset } from "./runtime-assets";
import { chapterIds } from "./config";
const props = defineProps<{ progress: number; reducedMotion: boolean }>();
const emit = defineEmits<{ ready: [] }>();
const rig = computed(() =>
  transitionAt(
    props.reducedMotion ? reducedProgress(props.progress) : props.progress,
  ),
);
const pair = ref({ from: "forest", to: "sky" }),
  loading = ref(true),
  failure = ref(false);
let sequence = 0,
  disposed = false;
const cache = new Map<string, Promise<void>>();
const heldRig = ref({ id: rig.value.id, local: rig.value.local });
const pending = new Set<() => void>();
function prepare(id: string) {
  if (!cache.has(id))
    cache.set(
      id,
      new Promise<void>((resolve, reject) => {
        const image = new Image();
        const finish = (error = false) => {
          clearTimeout(timeout);
          pending.delete(cancel);
          image.onload = null;
          image.onerror = null;
          error ? reject(new Error(id)) : resolve();
        };
        const cancel = () => {
          image.src = "";
          finish(true);
        };
        const timeout = setTimeout(cancel, 8000);
        pending.add(cancel);
        image.onload = () => finish();
        image.onerror = () => finish(true);
        image.src = sceneAsset(id, "primary");
      }),
    );
  return cache.get(id)!;
}
watch(
  () => `${rig.value.from}/${rig.value.to}`,
  async () => {
    const version = ++sequence,
      from = rig.value.from,
      to = rig.value.to;
    loading.value = true;
    failure.value = false;
    try {
      await Promise.all([prepare(from), prepare(to)]);
      if (disposed || version !== sequence) return;
      pair.value = { from, to };
      heldRig.value = { id: rig.value.id, local: rig.value.local };
      emit("ready");
      const next = chapterIds[chapterIds.indexOf(to) + 1];
      if (next) void prepare(next).catch(() => {});
    } catch {
      if (!disposed && version === sequence) {
        failure.value = true;
        emit("ready");
      }
    } finally {
      if (!disposed && version === sequence) loading.value = false;
    }
  },
  { immediate: true },
);
watch(rig, (value) => {
  if (pair.value.from === value.from && pair.value.to === value.to)
    heldRig.value = { id: value.id, local: value.local };
});
const clip = computed(() => {
  const p = heldRig.value.local;
  if (heldRig.value.id === "observation-data") {
    const inset = (1 - p) * 48;
    return `inset(${inset}% ${inset}% ${inset}% ${inset}% round ${12 * (1 - p)}px)`;
  }
  const y = 100 * (1 - p);
  return `polygon(0 ${y}%,25% ${Math.max(0, y - 2 * Math.sin(p * Math.PI))}%,60% ${y}%,100% ${Math.max(0, y - 1.4 * Math.sin(p * Math.PI))}%,100% 100%,0 100%)`;
});
onBeforeUnmount(() => {
  disposed = true;
  sequence++;
  pending.forEach((cancel) => cancel());
  pending.clear();
  cache.clear();
});
</script>
<template>
  <div class="sx-fallback-scene" data-testid="experience-fallback">
    <img :src="sceneAsset(pair.from, 'primary')" alt="" /><img
      :src="sceneAsset(pair.to, 'primary')"
      alt=""
      :style="{ clipPath: clip }"
    />
    <p>VERSION SIMPLIFIÉE 2D · IMAGES GÉNÉRÉES · MASQUE SPATIAL</p>
    <span v-if="loading" role="status">Chargement du prochain paysage…</span
    ><span v-if="failure" role="alert"
      >Un paysage est indisponible. Le récit et la navigation restent
      accessibles.</span
    >
  </div>
</template>
