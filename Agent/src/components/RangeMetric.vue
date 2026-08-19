<script setup lang="ts">
import type { KcalRange } from '@/api/qingheng'

defineProps<{
  label: string
  value: KcalRange
  tone?: 'green' | 'orange' | 'neutral'
  hint?: string
}>()
</script>

<template>
  <article class="metric" :class="`metric--${tone || 'green'}`">
    <div class="metric__head">
      <span>{{ label }}</span>
      <small v-if="hint">{{ hint }}</small>
    </div>
    <strong>{{ value.low === value.high ? value.low : `${value.low}–${value.high}` }} <em>kcal</em></strong>
    <div class="metric__track"><span /></div>
  </article>
</template>

<style scoped>
.metric {
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--qh-border);
  border-radius: 18px;
  background: var(--qh-card);
  box-shadow: var(--qh-shadow-soft);
}
.metric__head { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--qh-muted); font-size: 13px; }
.metric__head span { color: var(--qh-text); font-size: 15px; font-weight: 700; }
.metric strong { display: block; margin-top: 12px; color: var(--qh-green-dark); font-size: clamp(23px, 2.1vw, 31px); letter-spacing: -.04em; }
.metric em { font-size: 12px; font-style: normal; font-weight: 600; letter-spacing: 0; }
.metric__track { height: 8px; margin-top: 18px; overflow: hidden; border-radius: 999px; background: var(--qh-sage-soft); }
.metric__track span { display: block; width: 48%; height: 100%; margin-left: 27%; border-radius: inherit; background: var(--qh-green); }
.metric--orange strong { color: var(--qh-orange-dark); }
.metric--orange .metric__track { background: var(--qh-orange-soft); }
.metric--orange .metric__track span { background: var(--qh-orange); }
.metric--neutral strong { color: var(--qh-text); }
.metric--neutral .metric__track { background: #ebe8df; }
.metric--neutral .metric__track span { background: #8d8a80; }
</style>
