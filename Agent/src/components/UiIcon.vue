<script setup lang="ts">
defineProps<{ name: string }>()
const paths: Record<string, string> = {
  home: 'M3 11 12 3l9 8M5 10v11h5v-7h4v7h5V10',
  record: 'M7 3H5v18h14V7l-4-4H7Zm7 0v5h5M8 12h8M8 16h6',
  person: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM3 21v-2a9 6 0 0 1 18 0v2Z',
  camera: 'M3 7h4l2-3h6l2 3h4v14H3ZM16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  meal: 'M3 3v6q0 3 3 3t3-3V3M6 3v18M17 3q-4 5-2 9h4V3h-2Zm2 9v9',
  chart: 'M4 21V11h3v10ZM11 21V3h3v18ZM18 21V7h3v14Z',
  leaf: 'M4 20C2 7 10 2 21 3c1 12-7 18-17 17ZM4 20 16 8',
  activity: 'M15 5a2 2 0 1 1 0-4 2 2 0 0 1 0 4ZM5 10l5-3 4 3h5M10 7l-2 7 5 3-2 5M8 14l-4 7',
}
</script>
<template><svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.leaf" /></svg></template>
<style scoped>.ui-icon { width: 24px; height: 24px; flex-shrink: 0; vertical-align: middle; }</style>
