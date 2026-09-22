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
    <div class="metric__value">
      <strong>{{ value.low === value.high ? value.low : `${value.low}–${value.high}` }}</strong
      ><em>kcal</em>
    </div>
    <div class="metric__foot"><span>{{ value.low === value.high ? '估算值' : '估算区间' }}</span><i /></div>
  </article>
</template>

<style scoped>
.metric {
  position: relative;
  min-width: 0;
  overflow: hidden;
  padding: 19px 20px 17px;
  border: 1px solid var(--qh-border);
  border-radius: 16px;
  background: var(--qh-card);
  box-shadow: var(--qh-shadow-soft);
}
.metric::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 56px;
  height: 3px;
  background: var(--qh-green);
  content: '';
}
.metric__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--qh-muted);
  font-size: 13px;
}
.metric__head span {
  color: var(--qh-text);
  font-size: 14px;
  font-weight: 800;
}
.metric__head small {
  overflow: hidden;
  font-family: var(--qh-data);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric__value {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 12px;
}
.metric strong {
  color: var(--qh-green-dark);
  font-family: var(--qh-data);
  font-size: clamp(23px, 2.1vw, 31px);
  letter-spacing: -0.055em;
}
.metric em {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
  font-style: normal;
  font-weight: 600;
  letter-spacing: 0.06em;
}
.metric__foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 17px;
  color: var(--qh-muted);
  font-size: 12px;
  letter-spacing: 0.1em;
}
.metric__foot i {
  position: relative;
  flex: 1;
  height: 1px;
  background: var(--qh-border-strong);
}
.metric__foot i::before,
.metric__foot i::after {
  position: absolute;
  top: -2px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--qh-green);
  content: '';
}
.metric__foot i::before {
  left: 22%;
}
.metric__foot i::after {
  right: 12%;
}
.metric--orange strong {
  color: var(--qh-orange-dark);
}
.metric--orange::after,
.metric--orange .metric__foot i::before,
.metric--orange .metric__foot i::after {
  background: var(--qh-orange);
}
.metric--neutral strong {
  color: var(--qh-text);
}
.metric--neutral::after,
.metric--neutral .metric__foot i::before,
.metric--neutral .metric__foot i::after {
  background: #819087;
}
</style>
