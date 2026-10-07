<script setup lang="ts">
import UiIcon from './UiIcon.vue'
import type { KcalRange } from '@/api/qingheng'

defineProps<{
  icon?: string
  label: string
  value: KcalRange
  tone?: 'green' | 'orange' | 'neutral'
  hint?: string
  status?: string
  description?: string
}>()
</script>

<template>
  <article class="metric" :class="`metric--${tone || 'neutral'}`">
    <div class="metric__head">
      <span><UiIcon v-if="icon" :name="icon" /> {{ label }}</span>
      <details v-if="description" class="metric-info"><summary aria-label="了解热量缺口">ⓘ</summary><p>{{ description }}</p></details>
      <small v-if="hint">{{ hint }}</small>
    </div>
    <div class="metric__value">
      <strong>{{ value.low === value.high ? value.low.toLocaleString('zh-CN') : `${value.low.toLocaleString('zh-CN')}–${value.high.toLocaleString('zh-CN')}` }}</strong
      ><em>kcal</em>
    </div>
    <div class="metric__foot"><span>{{ status && hint ? hint : value.low === value.high ? '估算值' : '估算区间' }}</span><b v-if="status" class="metric__status">{{ status }}</b></div>
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
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--qh-muted);
  font-size: 13px;
}
.metric-info { margin: 0 auto 0 0; }
.metric-info summary { cursor: pointer; list-style: none; font-size: 16px; }
.metric-info summary::-webkit-details-marker { display: none; }
.metric-info p { position: absolute; left: 0; top: 22px; z-index: 3; max-width: 100%; margin: 4px 0 0; padding: 12px; background: #fffcf8; color: var(--qh-text); border: 1px solid var(--qh-border); border-radius: 10px; font-size: 12px; line-height: 1.7; box-shadow: var(--qh-shadow-soft); }
.metric__head span {
  color: var(--qh-text);
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  font-size: 14px;
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
  flex-wrap: wrap;
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
  justify-content: space-between;
  gap: 8px;
  margin-top: 17px;
  color: var(--qh-muted);
  font-size: 12px;
  letter-spacing: 0.1em;
}
.metric__status { font-size: 12px; padding: 5px 10px; border-radius: 999px; color: var(--qh-green-dark); background: #ffffffb3; }
.metric--orange .metric__status { color: var(--qh-orange-dark); }
.metric { transition: background-color 350ms ease, border-color 350ms ease; }
.metric--orange strong {
  color: var(--qh-orange-dark);
}
.metric--orange::after {
  background: var(--qh-orange);
}
.metric--neutral strong {
  color: var(--qh-text);
}
.metric--neutral::after {
  background: #819087;
}
.metric__head .ui-icon {
  width: 18px;
  height: 18px;
}
</style>
