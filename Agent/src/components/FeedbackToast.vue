<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { useQinghengStore } from '@/stores/qingheng'
const store = useQinghengStore()
let timer: ReturnType<typeof setTimeout> | undefined
watch(() => store.notice, notice => {
  if (timer) clearTimeout(timer)
  if (notice) timer = setTimeout(() => store.clearNotice(), 5000)
}, { immediate: true })
onBeforeUnmount(() => { if (timer) clearTimeout(timer) })
function dismiss() { store.clearError(); store.clearNotice() }
</script>

<template>
  <div class="feedback-host">
    <div v-if="store.error" class="feedback-toast feedback-toast--error" role="alert"><span class="status-mark" aria-hidden="true">!</span><p>{{ store.error }}</p><button type="button" aria-label="关闭错误提示" @click="dismiss">×</button></div>
    <div v-else-if="store.notice" :key="store.notice.id" class="feedback-toast" role="status"><span class="status-mark" aria-hidden="true">✓</span><p>{{ store.notice.text }}</p><button type="button" aria-label="关闭成功提示" @click="dismiss">×</button></div>
  </div>
</template>

<style scoped>
.feedback-host { position: fixed; z-index: 80; top: max(16px, env(safe-area-inset-top)); right: 20px; width: min(420px, calc(100vw - 32px)); pointer-events: none; }
.feedback-toast { display: flex; align-items: center; gap: 10px; padding: 12px 12px 12px 16px; border: 1px solid var(--qh-border-strong); border-radius: 18px; background: var(--qh-cream); box-shadow: 0 5px 0 color-mix(in srgb, var(--qh-berry) 10%, transparent); pointer-events: auto; }
.status-mark { display: grid; place-items: center; flex: 0 0 28px; width: 28px; height: 28px; border-radius: 50%; background: var(--qh-mint); color: var(--qh-berry); font-size: 17px; font-weight: 700; }
.feedback-toast--error .status-mark { background: var(--qh-yellow); }
p { margin: 0; flex: 1; min-width: 0; color: var(--qh-muted); font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
button { flex: 0 0 40px; min-height: 44px; border: 0; border-radius: 12px; background: var(--qh-oat); color: var(--qh-muted); font-size: 22px; cursor: pointer; }
@media (max-width: 760px) { .feedback-host { right: 16px; } }
</style>
