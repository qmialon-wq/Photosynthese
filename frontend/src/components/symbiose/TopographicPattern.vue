<template>
  <svg
    class="sym-topography"
    viewBox="0 0 200 180"
    fill="none"
    aria-hidden="true"
  >
    <path
      v-for="i in 9"
      :key="i"
      d="M20 190C30 170 16 133 44 119S76 134 84 101S68 67 106 62S129 88 148 52S150 2 211-5"
      :transform="`translate(${-i * 9} ${-i * 8})`"
    />
  </svg>
</template>
