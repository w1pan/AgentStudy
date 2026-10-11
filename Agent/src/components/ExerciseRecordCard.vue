<script setup lang="ts">
import { computed } from 'vue'
import type { Exercise } from '@/api/qingheng'
import UiIcon from './UiIcon.vue'

const props = defineProps<{ exercise: Exercise; busy?: boolean; readonly?: boolean }>()
defineEmits<{ edit: [exercise: Exercise]; remove: [exercise: Exercise] }>()
const intensityLabel = computed(() => ({ low: '较低', medium: '中等', high: '较高' })[props.exercise.intensity])
const kcalText = computed(() => {
  const { low, high } = props.exercise.kcal
  return low === high ? low.toLocaleString('zh-CN') : `${low.toLocaleString('zh-CN')}–${high.toLocaleString('zh-CN')}`
})
const recordLabel = computed(() => `${props.exercise.activity_name} ${props.exercise.recorded_time.slice(0, 5)}`)
</script>

<template>
  <details class="qh-disclosure exercise-card">
    <summary class="exercise-summary">
      <span class="exercise-icon"><UiIcon name="activity" /></span>
      <span class="exercise-heading">
        <strong>{{ exercise.activity_name }}</strong>
        <span class="exercise-meta"><b>{{ exercise.duration_minutes }} 分钟</b><span aria-hidden="true"> · </span><time :datetime="exercise.recorded_time">{{ exercise.recorded_time.slice(0, 5) }}</time></span>
      </span>
      <span class="exercise-energy"><small>预计消耗</small><span><strong>{{ kcalText }}</strong><small>kcal</small></span></span>
    </summary>

    <div class="exercise-body">
      <dl class="exercise-facts">
        <div><dt>运动强度</dt><dd>{{ intensityLabel }}</dd></div>
        <div><dt>热量来源</dt><dd>{{ exercise.estimate_source === 'met' ? 'MET 估算' : '手动修正' }}</dd></div>
      </dl>
      <p class="exercise-note">{{ exercise.estimate_source === 'met'
        ? '根据运动项目、强度、时长与体重估算消耗。'
        : '采用这条记录中填写的修正热量区间。' }}</p>
      <footer v-if="!readonly && (exercise.editable || exercise.deletable)" class="exercise-actions">
        <button v-if="exercise.editable" class="exercise-edit" :disabled="busy" :aria-label="`编辑${recordLabel}的运动记录`" @click="$emit('edit', exercise)">编辑运动</button>
        <button v-if="exercise.deletable" class="exercise-delete" :disabled="busy" :aria-label="`删除${recordLabel}的运动记录`" @click="$emit('remove', exercise)">删除记录</button>
      </footer>
    </div>
  </details>
</template>

<style scoped>
.exercise-card { min-width: 0; container-type: inline-size; }
.exercise-card > .exercise-summary { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 18px 48px 18px 18px; }
.exercise-summary::before, .exercise-summary::after { right: 18px; }
.exercise-summary:focus-visible { outline-offset: -4px; }
.exercise-summary:hover { background: color-mix(in srgb, var(--qh-oat) 94%, var(--qh-berry)); }
.exercise-card[open] > .exercise-summary { border-bottom: 1px solid var(--qh-border); }
.exercise-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; color: white; background: var(--qh-berry); }
.exercise-icon .ui-icon { width: 22px; height: 22px; }
.exercise-heading { display: grid; gap: 6px; min-width: 0; }
.exercise-heading > strong { font-size: 18px; line-height: 1.4; overflow-wrap: anywhere; }
.exercise-meta { color: var(--qh-muted); font-family: var(--qh-numeral); font-size: 13px; font-weight: 400; }
.exercise-meta b { color: var(--qh-text); font-weight: 600; }
.exercise-energy { display: grid; gap: 2px; max-width: 180px; text-align: right; }
.exercise-energy small { font-size: 12px; font-weight: 400; color: var(--qh-muted); }
.exercise-energy > span { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: flex-end; gap: 2px 5px; }
.exercise-energy strong { font-family: var(--qh-numeral); font-size: 24px; letter-spacing: -.035em; overflow-wrap: anywhere; }
.exercise-body { padding: 16px 18px; }
.exercise-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 0; }
.exercise-facts dt { font-size: 12px; color: var(--qh-muted); }
.exercise-facts dd { margin: 4px 0 0; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.exercise-note { margin: 12px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.7; }
.exercise-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--qh-border); }
.exercise-actions button { min-height: 40px; padding: 8px 14px; border-radius: var(--qh-radius-pill); border: 1px solid var(--qh-border-strong); cursor: pointer; font-size: 13px; }
.exercise-edit { color: var(--qh-on-brand); background: var(--qh-brand); }
.exercise-edit:not(:disabled):hover { background: var(--qh-brand-hover); }
.exercise-delete { color: var(--qh-muted); background: transparent; }
.exercise-delete:not(:disabled):hover { color: var(--qh-danger); background: var(--qh-brand-soft); }
.exercise-actions button:disabled { opacity: .55; cursor: wait; }
@container (max-width: 480px) {
  .exercise-card > .exercise-summary { grid-template-columns: 32px minmax(0, 1fr); gap: 10px; padding: 14px 40px 14px 14px; }
  .exercise-icon { width: 32px; height: 32px; align-self: start; }
  .exercise-heading > strong { font-size: 17px; }
  .exercise-energy { grid-column: 2; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px; max-width: none; text-align: left; }
  .exercise-energy > span { justify-content: flex-start; }
  .exercise-energy strong { font-size: 22px; }
  .exercise-body { padding: 14px; }
  .exercise-actions { justify-content: flex-start; }
  .exercise-actions button { min-height: 44px; }
}
</style>
