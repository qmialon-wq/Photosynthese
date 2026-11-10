<script setup lang="ts">
import { onMounted } from "vue";
import { useWallpaper } from "../../composables/useWallpaper";
const wallpaper = useWallpaper();
onMounted(wallpaper.initialize);
</script>
<template>
  <div
    class="sym-forest"
    aria-hidden="true"
    :data-wallpaper="wallpaper.selected.value.id"
    :class="{ 'is-reduced': wallpaper.reduced.value }"
  >
    <div
      class="sym-wallpaper-layer"
      :style="{
        backgroundImage: `url('${wallpaper.base.value.image}')`,
        backgroundPosition: wallpaper.base.value.position,
      }"
    >
      <div
        class="sym-wallpaper-overlay"
        :style="{ background: wallpaper.base.value.overlay }"
      />
    </div>
    <div
      v-if="wallpaper.incoming.value"
      class="sym-wallpaper-layer sym-wallpaper-incoming"
      :class="{ 'is-visible': wallpaper.incomingVisible.value }"
      :style="{
        backgroundImage: `url('${wallpaper.incoming.value.image}')`,
        backgroundPosition: wallpaper.incoming.value.position,
      }"
    >
      <div
        class="sym-wallpaper-overlay"
        :style="{ background: wallpaper.incoming.value.overlay }"
      />
    </div>
  </div>
</template>
