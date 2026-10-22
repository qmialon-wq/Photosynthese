<script setup lang="ts">
import { ref } from "vue";
import type { Box } from "../types";
const props = defineProps<{
  modelValue: Box;
  src: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [box: Box] }>();
const surface = ref<HTMLElement | null>(null);
const start = ref<{ x: number; y: number } | null>(null);
const failed = ref(false);
function point(event: PointerEvent) {
  const rect = surface.value!.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
  };
}
function down(event: PointerEvent) {
  if (props.disabled) return;
  surface.value?.setPointerCapture(event.pointerId);
  start.value = point(event);
}
function move(event: PointerEvent) {
  if (!start.value || props.disabled) return;
  const end = point(event);
  const box = {
    x: Math.min(start.value.x, end.x),
    y: Math.min(start.value.y, end.y),
    w: Math.abs(start.value.x - end.x),
    h: Math.abs(start.value.y - end.y),
  };
  if (box.w >= 0.001 && box.h >= 0.001) emit("update:modelValue", box);
}
function update(key: keyof Box, event: Event) {
  const number = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(number)) return;
  const box = { ...props.modelValue, [key]: number };
  box.x = Math.max(0, Math.min(0.999, box.x));
  box.y = Math.max(0, Math.min(0.999, box.y));
  box.w = Math.max(0.001, Math.min(1 - box.x, box.w));
  box.h = Math.max(0.001, Math.min(1 - box.y, box.h));
  emit("update:modelValue", box);
}
function keyboard(event: KeyboardEvent) {
  if (
    props.disabled ||
    !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)
  )
    return;
  event.preventDefault();
  const box = { ...props.modelValue };
  const step = event.shiftKey ? 0.02 : 0.002;
  box.x = Math.max(
    0,
    Math.min(
      1 - box.w,
      box.x +
        (event.key === "ArrowRight"
          ? step
          : event.key === "ArrowLeft"
            ? -step
            : 0),
    ),
  );
  box.y = Math.max(
    0,
    Math.min(
      1 - box.h,
      box.y +
        (event.key === "ArrowDown"
          ? step
          : event.key === "ArrowUp"
            ? -step
            : 0),
    ),
  );
  emit("update:modelValue", box);
}
</script>
<template>
  <div class="box-editor">
    <p id="box-help" class="muted">
      Dessinez une boîte sur l’image originale. Au clavier : flèches pour
      déplacer, champs numériques pour redimensionner.
    </p>
    <div
      ref="surface"
      class="box-surface"
      tabindex="0"
      role="group"
      aria-label="Éditeur de bounding box"
      aria-describedby="box-help"
      :aria-disabled="disabled"
      @pointerdown.prevent="down"
      @pointermove="move"
      @pointerup="start = null"
      @pointercancel="start = null"
      @keydown="keyboard"
    >
      <img
        :src="src"
        alt="Image originale à annoter"
        draggable="false"
        @error="failed = true"
      />
      <div
        class="annotation-box"
        :style="{
          left: `${modelValue.x * 100}%`,
          top: `${modelValue.y * 100}%`,
          width: `${modelValue.w * 100}%`,
          height: `${modelValue.h * 100}%`,
        }"
        aria-hidden="true"
      >
        <span>Animal</span>
      </div>
    </div>
    <p v-if="failed" role="alert">Image originale indisponible.</p>
    <div class="box-fields">
      <label
        v-for="(title, key) in { x: 'X', y: 'Y', w: 'Largeur', h: 'Hauteur' }"
        :key="key"
        >{{ title }}
        <input
          type="number"
          :aria-label="title"
          :value="Number(modelValue[key].toFixed(4))"
          step="0.001"
          min="0"
          max="1"
          :disabled="disabled"
          @change="update(key, $event)"
      /></label>
    </div>
  </div>
</template>
