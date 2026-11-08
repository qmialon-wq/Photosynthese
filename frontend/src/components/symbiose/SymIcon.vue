<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 24 });
const paths: Record<string, string[]> = {
  grid: ["M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h6v6h-6z"],
  video: [
    "M3 5h11a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z",
    "m15 9 7-4v14l-7-4",
  ],
  folder: ["M3 5h6l2 3h10v12H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z"],
  sparkles: [
    "m10 2 2.3 6.7L19 11l-6.7 2.3L10 20l-2.3-6.7L1 11l6.7-2.3L10 2Z",
    "M20 2v5 M17.5 4.5h5 M20 16v6 M17 19h6",
  ],
  "check-square": ["M20 12v8H3V3h13", "m7 10 4 4L22 3"],
  document: [
    "M5 2h14a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z",
    "M8 7h8 M8 12h8 M8 17h6",
  ],
  search: ["M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z", "m15 15 6 6"],
  bell: [
    "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Z",
    "M10 21h4 M12 1v2",
  ],
  user: [
    "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
    "M16 9a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    "M5 19c1-6 13-6 14 0",
  ],
  settings: [
    "m10 2-.8 3-2 .9-2.8-.8L2 9l2.3 2.2v2L2 15.5l2.4 3.8 2.8-.8 2 .9.8 2.6h4l.8-2.6 2-.9 2.8.8 2.4-3.8-2.3-2.3v-2L22 9l-2.4-3.9-2.8.8-2-.9L14 2h-4Z",
    "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
  ],
  pin: [
    "M20 10c0 6-8 13-8 13S4 16 4 10a8 8 0 1 1 16 0Z",
    "M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  ],
  camera: [
    "M3 6h4l2-3h6l2 3h4a1 1 0 0 1 1 1v13H2V7a1 1 0 0 1 1-1Z",
    "M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0Z",
  ],
  paw: [
    "M8 13c2-4 6-4 8 0l3 5c1 4-3 4-7 3-4 1-8 1-7-3l3-5Z",
    "M5 7c0 4-4 4-4 0s4-4 4 0Z M11 4c0 4-4 4-4 0s4-4 4 0Z M17 4c0 4-4 4-4 0s4-4 4 0Z M23 7c0 4-4 4-4 0s4-4 4 0Z",
  ],
  leaf: ["M3 21C0 6 9 7 22 2c0 16-8 21-16 15", "M2 22 17 8"],
  sprout: [
    "M12 22V11 M6 22h12",
    "M12 11C4 12 2 6 3 3c7 0 10 2 9 8Z M12 16c8 1 10-5 9-8-7 0-10 2-9 8Z",
  ],
  arrow: ["M3 12h18 m-6-6 6 6-6 6"],
  chevron: ["m9 4 8 8-8 8"],
  check: ["m4 12 5 5L20 6"],
  layers: ["m12 2 10 5-10 5L2 7l10-5Z M2 12l10 5 10-5 M2 17l10 5 10-5"],
  connection: [
    "M5 5 19 19 M5 19 19 5",
    "M7 4a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z M23 4a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z M7 20a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z M23 20a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  ],
  hourglass: [
    "M5 2h14 M5 22h14 M6 2v4c0 3 12 9 12 12v4 M18 2v4c0 3-12 9-12 12v4",
  ],
  close: ["m5 5 14 14 M19 5 5 19"],
  plus: ["M12 3v18 M3 12h18"],
  clock: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z", "M12 5v7l5 3"],
  trash: ["M3 5h18 M9 5V2h6v3 M5 5l1 17h12l1-17 M10 9v8 M14 9v8"],
  calendar: ["M3 5h18v17H3z M7 2v6 M17 2v6 M3 10h18 M7 14h2 M13 14h2 M7 18h2"],
  refresh: ["M21 10a9 9 0 1 0-2 8", "M21 3v7h-7"],
  more: ["M4 12h.01 M12 12h.01 M20 12h.01"],
  file: ["M5 2h9l5 5v15H5z M14 2v6h5"],
  sliders: [
    "M2 5h5 M11 5h11 M2 12h11 M17 12h5 M2 19h5 M11 19h11",
    "M11 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z M17 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z M11 19a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z",
  ],
  play: ["m7 3 14 9-14 9V3Z"],
  pause: ["M6 3h3v18H6z M15 3h3v18h-3z"],
  volume: ["M3 9h4l5-5v16l-5-5H3z M16 7c4 2 4 8 0 10 M19 3c7 5 7 13 0 18"],
  "volume-off": ["M3 9h4l5-5v16l-5-5H3z M17 9l5 6 M22 9l-5 6"],
  fullscreen: ["M3 9V3h6 M15 3h6v6 M21 15v6h-6 M9 21H3v-6"],
  info: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z M12 11v6 M12 7h.01"],
  download: ["M12 2v13 m-5-5 5 5 5-5 M3 15v6h18v-6"],
  upload: ["M12 16V2 m-5 5 5-5 5 5 M3 15v6h18v-6"],
  inbox: ["M3 13 6 3h12l3 10v8H3z M3 13h5l2 4h4l2-4h5"],
  chart: ["M3 15h4v7H3z M10 8h4v14h-4z M17 2h4v20h-4z"],
};
</script>
<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="sym-icon"
  >
    <path v-for="(d, index) in paths[name] || paths.grid" :key="index" :d="d" />
  </svg>
</template>
