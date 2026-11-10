<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
const props = defineProps<{
  latitude: number | null;
  longitude: number | null;
  disabled?: boolean;
}>();
const emit = defineEmits<{ select: [latitude: number, longitude: number] }>();
const element = ref<HTMLElement>();
let map: L.Map | undefined;
let marker: L.CircleMarker | undefined;
function update() {
  if (!map) return;
  if (
    props.latitude == null ||
    props.longitude == null ||
    !Number.isFinite(props.latitude) ||
    !Number.isFinite(props.longitude) ||
    Math.abs(props.latitude) > 90 ||
    Math.abs(props.longitude) > 180
  ) {
    marker?.remove();
    marker = undefined;
    return;
  }
  const point: L.LatLngTuple = [props.latitude, props.longitude];
  if (marker) marker.setLatLng(point);
  else
    marker = L.circleMarker(point, {
      radius: 7,
      color: "#195c42",
      fillOpacity: 0.8,
    }).addTo(map);
  marker.bindTooltip("Point interrogé uniquement");
  map.panTo(point);
}
onMounted(() => {
  if (!element.value) return;
  map = L.map(element.value).setView([49.18, -0.37], 10);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  map.on("click", (event: L.LeafletMouseEvent) => {
    if (!props.disabled)
      emit(
        "select",
        Number(event.latlng.lat.toFixed(6)),
        Number(event.latlng.lng.toFixed(6)),
      );
  });
  update();
});
watch(() => [props.latitude, props.longitude], update);
onBeforeUnmount(() => map?.remove());
</script>
<template>
  <div
    ref="element"
    class="territorial-point-map"
    aria-label="Carte de sélection du point. La saisie latitude et longitude est disponible juste après."
  />
</template>
<style scoped>
.territorial-point-map {
  height: 280px;
  border-radius: 12px;
  z-index: 0;
}
</style>
