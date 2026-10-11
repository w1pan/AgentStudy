<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import MealRecordCard from '@/components/MealRecordCard.vue'
import ExerciseRecordCard from '@/components/ExerciseRecordCard.vue'
import UiIcon from '@/components/UiIcon.vue'
import MonthPicker from '@/components/MonthPicker.vue'
import { api, type DayDetail, type KcalRange } from '@/api/qingheng'

function localDatePart(part: 'month' | 'date') {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  if (part === 'month') return `${year}-${month}`
  return `${year}-${month}-${String(now.getDate()).padStart(2, '0')}`
}

const currentMonth = localDatePart('month')
const currentDate = localDatePart('date')
const month = ref(currentMonth)
const dates = ref<string[]>([])
const selectedDate = ref('')
const detail = ref<DayDetail | null>(null)
const loading = ref(false)
const localError = ref('')
let requestVersion = 0

function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

const monthTitle = computed(() => `${month.value.slice(0, 4)} 年 ${Number(month.value.slice(5))} 月`)
const weekday = (value: string) => new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(new Date(`${value}T00:00:00`))
const formatRange = (value: KcalRange) => value.low === value.high
  ? value.low.toLocaleString('zh-CN')
  : `${value.low.toLocaleString('zh-CN')}–${value.high.toLocaleString('zh-CN')}`
function stepMonth(step: number) {
  const date = new Date(`${month.value}-01T00:00:00`)
  date.setMonth(date.getMonth() + step)
  month.value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

async function loadMonth() {
  const version = ++requestVersion
  loading.value = true
  localError.value = ''
  dates.value = []
  selectedDate.value = ''
  detail.value = null
  try {
    const response = await api.getHistoryMonth(month.value)
    if (version !== requestVersion) return
    dates.value = response.dates
    selectedDate.value = response.dates[response.dates.length - 1] || ''
    const result = selectedDate.value ? await api.getHistoryDay(selectedDate.value) : null
    if (version === requestVersion) detail.value = result
  } catch (error) {
    if (version !== requestVersion) return
    localError.value = error instanceof Error ? error.message : '历史记录加载失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function selectDate(value: string) {
  const version = ++requestVersion
  selectedDate.value = value
  detail.value = null
  loading.value = true
  localError.value = ''
  try {
    const result = await api.getHistoryDay(value)
    if (version === requestVersion) detail.value = result
  } catch (error) {
    if (version !== requestVersion) return
    localError.value = error instanceof Error ? error.message : '日期详情加载失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(month, loadMonth, { flush: 'sync' })
onMounted(loadMonth)
onBeforeUnmount(() => { requestVersion += 1 })
</script>

<template>
  <main class="records-page">
    <header class="page-header">
      <div><p class="eyebrow">每日手账</p><h1>记录</h1><p class="page-intro">翻到某一天，看看吃过什么、做过什么。</p></div>
      <div class="month-controls">
        <button type="button" aria-label="上个月" @click="stepMonth(-1)">‹</button>
        <MonthPicker v-model="month" :max="currentMonth" />
        <button type="button" aria-label="下个月" :disabled="month >= currentMonth" @click="stepMonth(1)">›</button>
      </div>
    </header>

    <div v-if="localError" class="error-banner" role="alert"><p class="form-error">{{ localError }}</p><button @click="selectedDate ? selectDate(selectedDate) : loadMonth()">重新加载</button></div>
    <section class="records-layout">
      <aside class="date-list panel" aria-label="有记录的日期">
        <header><strong>{{ monthTitle }}</strong><small>{{ dates.length }} 个记录日</small></header>
        <div class="date-buttons">
          <button v-for="value in dates" :key="value" :class="{ active: selectedDate === value }" :aria-pressed="selectedDate === value" :aria-label="`${value} ${weekday(value)}`" @click="selectDate(value)">
            <span class="date-number">{{ Number(value.slice(-2)) }}</span>
            <span class="date-caption"><strong>{{ weekday(value) }}</strong><small>{{ value === currentDate ? '今天' : formatDate(value) }}</small></span>
            <span class="date-dot" aria-hidden="true"></span>
          </button>
        </div>
        <div v-if="!dates.length && !loading" class="empty-dates">这个月还没有记录</div>
      </aside>

      <div v-if="detail" :key="selectedDate" class="day-detail">
        <header class="day-heading"><div><p class="eyebrow">{{ selectedDate }} · {{ weekday(selectedDate) }}</p><h2>{{ formatDate(selectedDate) }}的手账</h2></div><span class="readonly-badge">{{ selectedDate === currentDate ? '修改请前往今日页' : '历史只读' }}</span></header>
        <section class="energy-summary panel" aria-label="当日能量摘要">
          <div class="summary-metrics">
            <article class="summary-metric"><span class="metric-label"><span class="metric-icon intake-icon"><UiIcon name="meal" /></span>已记录摄入</span><p><strong>{{ detail.meals.length ? formatRange(detail.summary.intake) : '—' }}</strong><small v-if="detail.meals.length">kcal</small></p><span class="metric-note">{{ detail.meals.length ? `${detail.meals.length} 餐已记` : '当天未记录饮食' }}</span></article>
            <article class="summary-metric"><span class="metric-label"><span class="metric-icon flame-icon"><UiIcon name="flame" /></span>预计消耗</span><p><strong>{{ formatRange(detail.summary.total_expenditure) }}</strong><small>kcal</small></p><span class="metric-note">日常消耗 + 已记录活动</span></article>
            <article class="summary-metric balance-metric"><span class="metric-label"><span class="metric-icon balance-icon"><UiIcon name="chart" /></span>估算缺口 / 盈余</span><p><strong>{{ detail.meals.length ? formatRange(detail.summary.deficit) : '—' }}</strong><small v-if="detail.meals.length">kcal</small></p><span class="metric-note">{{ detail.meals.length ? `目标缺口 ${formatRange(detail.summary.target_deficit)} kcal` : '记录饮食后可估算' }}</span></article>
          </div>
          <p class="summary-note">按当天已记录数据估算；正值为缺口，负值为盈余。未记全的餐食会影响结果。</p>
        </section>

        <section class="panel detail-panel">
          <header><h3><span class="section-icon meal-section-icon"><UiIcon name="meal" /></span>当日餐食</h3><span>{{ detail.meals.length }} 餐已记</span></header>
          <div v-if="detail.meals.length" class="record-cards"><MealRecordCard v-for="meal in detail.meals" :key="meal.id" :meal="meal" readonly /></div>
          <p v-else class="empty-copy">当天没有饮食记录。</p>
        </section>

        <section class="two-panels">
          <section class="panel detail-panel activity-panel">
            <header><h3><span class="section-icon activity-section-icon"><UiIcon name="activity" /></span>活动记录</h3><span>{{ detail.exercises.length }} 次活动</span></header>
            <div v-if="detail.exercises.length" class="record-cards"><ExerciseRecordCard v-for="exercise in detail.exercises" :key="exercise.id" :exercise="exercise" readonly /></div>
            <p v-else class="empty-copy">当天没有运动记录。</p>
          </section>
          <section class="panel weight-history"><header><h3><span class="section-icon weight-section-icon"><UiIcon name="scale" /></span>当日体重</h3></header><div class="weight-value"><strong>{{ detail.weight ? detail.weight.weight_kg : '—' }}</strong><span v-if="detail.weight">kg</span></div><p>{{ detail.weight ? '当天保存的体重' : '当天未记录体重' }}</p></section>
        </section>
      </div>

      <section v-else-if="loading" class="no-selection panel" role="status"><span class="empty-icon"><UiIcon name="record" /></span><strong>正在加载记录…</strong></section>
      <section v-else-if="!localError" class="no-selection panel"><span class="empty-icon"><UiIcon name="record" /></span><strong>没有可查看的日期</strong><p>可以切换月份，或从今日页开始记录。<br />有记录的日期会出现在这里。</p></section>
    </section>
  </main>
</template>

<style scoped>
.records-page { width: min(1360px, 100%); margin: 0 auto; padding: 30px 28px 40px; }
.page-header { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 26px; }
.eyebrow { margin: 0; color: var(--qh-muted); font-size: 12px; font-weight: 600; letter-spacing: .08em; }
.page-header h1 { margin: 5px 0 8px; font-size: 36px; letter-spacing: -.04em; }
.page-intro { margin: 0; color: var(--qh-muted); font-size: 14px; line-height: 1.7; }
.month-controls { display: flex; align-items: end; gap: 8px; }
.month-controls > button { width: 42px; height: 44px; border: 1px solid var(--qh-border); border-radius: 50%; background: var(--qh-oat); color: var(--qh-berry); font-size: 24px; cursor: pointer; }
.month-controls > button:disabled { opacity: .35; cursor: default; }
.records-layout { display: grid; grid-template-columns: 190px minmax(0, 1fr); align-items: start; gap: 22px; }
.panel { min-width: 0; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-card); background: var(--qh-cream); }
.date-list { overflow: hidden; }
.date-list > header { display: grid; gap: 6px; padding: 20px 16px; border-bottom: 1px solid var(--qh-border); background: var(--qh-oat); }
.date-list header strong { font-size: 16px; }
.date-list header small { color: var(--qh-muted); font-size: 12px; }
.date-buttons { display: grid; gap: 6px; padding: 8px; max-height: 560px; overflow-y: auto; }
.date-buttons:empty { display: none; }
.date-buttons button { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 66px; padding: 10px; border: 1px solid transparent; border-radius: 14px; text-align: left; color: var(--qh-berry); background: transparent; cursor: pointer; }
.date-buttons button:hover { background: var(--qh-oat); }
.date-buttons button.active { color: white; background: var(--qh-berry); }
.date-buttons button:focus-visible { outline-offset: -3px; }
.date-number { font-family: var(--qh-numeral); font-size: 28px; font-weight: 700; line-height: 1; min-width: 34px; text-align: center; }
.date-caption { display: grid; gap: 4px; }
.date-caption strong { font-size: 13px; font-weight: 600; }
.date-caption small { color: var(--qh-muted); font-size: 11px; }
.active .date-caption small { color: white; }
.date-dot { width: 5px; height: 5px; margin-left: auto; border-radius: 50%; background: currentColor; opacity: .6; }
.empty-dates { padding: 28px 12px; color: var(--qh-muted); font-size: 12px; text-align: center; }
.day-detail { min-width: 0; display: grid; gap: 18px; }
.day-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.day-heading h2 { margin: 5px 0 0; font-size: 26px; }
.readonly-badge { padding: 7px 11px; border-radius: var(--qh-radius-pill); color: var(--qh-muted); background: var(--qh-oat); font-size: 12px; }
.energy-summary { overflow: hidden; }
.summary-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); background: var(--qh-oat); }
.summary-metric { min-width: 0; padding: 18px; }
.summary-metric + .summary-metric { border-left: 1px solid var(--qh-border); }
.metric-label { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; }
.metric-icon, .section-icon { display: inline-grid; place-items: center; flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%; }
.metric-icon .ui-icon, .section-icon .ui-icon { width: 18px; height: 18px; }
.intake-icon { background: var(--qh-pink); }
.flame-icon { color: var(--qh-red); background: color-mix(in srgb, var(--qh-yellow) 60%, var(--qh-cream)); }
.balance-icon, .meal-section-icon { background: var(--qh-mint); }
.summary-metric p { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 6px; margin: 14px 0 7px; }
.summary-metric p strong { font-family: var(--qh-numeral); font-size: clamp(22px, 2.2vw, 30px); letter-spacing: -.04em; overflow-wrap: anywhere; }
.summary-metric p small { font-size: 11px; }
.metric-note { display: block; color: var(--qh-muted); font-size: 12px; line-height: 1.6; }
.summary-note { margin: 0; padding: 12px 18px; border-top: 1px solid var(--qh-border); color: var(--qh-muted); font-size: 12px; line-height: 1.7; }
.detail-panel > header, .weight-history > header { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 16px 18px; border-bottom: 1px solid var(--qh-border); border-radius: 21px 21px 0 0; background: var(--qh-oat); }
.panel h3 { display: flex; align-items: center; gap: 9px; margin: 0; font-size: 19px; }
.detail-panel > header > span { flex-shrink: 0; color: var(--qh-muted); font-size: 12px; }
.record-cards { display: grid; gap: 12px; padding: 16px; }
.empty-copy { margin: 0; padding: 26px 20px; color: var(--qh-muted); font-size: 13px; }
.two-panels { display: grid; grid-template-columns: minmax(0, 1fr) 230px; align-items: start; gap: 18px; }
.activity-section-icon { color: white; background: var(--qh-berry); }
.weight-section-icon { background: var(--qh-blue); }
.weight-value { display: flex; align-items: baseline; gap: 7px; padding: 20px 20px 0; font-family: var(--qh-numeral); }
.weight-value strong { font-size: 32px; }
.weight-value span { font-size: 13px; }
.weight-history > p { margin: 8px 20px 20px; color: var(--qh-muted); font-size: 12px; }
.no-selection { display: grid; min-height: 350px; padding: 28px; place-items: center; align-content: center; text-align: center; }
.empty-icon { display: grid; width: 52px; height: 52px; place-items: center; border-radius: 50%; background: var(--qh-oat); }
.empty-icon .ui-icon { width: 25px; height: 25px; }
.no-selection strong { margin-top: 16px; font-size: 18px; }
.no-selection p { margin-bottom: 0; color: var(--qh-muted); font-size: 13px; line-height: 1.8; }
.error-banner { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; padding: 12px 16px; border: 1px solid var(--qh-border); border-radius: 14px; background: var(--qh-oat); }
.form-error { margin: 0; color: var(--qh-danger); overflow-wrap: anywhere; }
.error-banner button { flex-shrink: 0; min-height: 44px; padding: 8px 12px; border: 1px solid var(--qh-border-strong); border-radius: var(--qh-radius-pill); background: var(--qh-cream); color: var(--qh-berry); cursor: pointer; }
@media (max-width: 1150px) {
  .records-layout { grid-template-columns: 160px minmax(0, 1fr); gap: 16px; }
  .summary-metric { padding: 14px 12px; }
  .metric-label { flex-wrap: wrap; }
  .two-panels { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 950px) {
  .records-layout { grid-template-columns: minmax(0, 1fr); }
  .date-list > header { display: flex; align-items: baseline; justify-content: space-between; padding: 14px 16px; }
  .date-buttons { display: flex; overflow-x: auto; max-height: none; gap: 8px; }
  .date-buttons button { flex: 0 0 108px; gap: 8px; }
  .date-dot { display: none; }
}
@media (max-width: 760px) {
  .records-page { padding: 22px 12px calc(96px + env(safe-area-inset-bottom)); }
  .page-header { flex-direction: column; align-items: stretch; gap: 18px; margin-bottom: 20px; }
  .page-header h1 { font-size: 30px; }
  .month-controls { align-items: end; }
  .month-controls > button { width: 44px; flex-shrink: 0; }
  .day-heading h2 { font-size: 23px; }
  .summary-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .balance-metric { grid-column: 1 / -1; }
  .summary-metric.balance-metric { border-left: 0; border-top: 1px solid var(--qh-border); }
  .summary-metric p strong { font-size: 25px; }
  .metric-label { gap: 6px; font-size: 12px; }
  .metric-icon { width: 26px; height: 26px; }
  .record-cards { padding: 12px; }
  .detail-panel > header, .weight-history > header { padding: 14px; }
  .panel h3 { font-size: 18px; }
  .summary-note { padding: 12px; }
  .no-selection { min-height: 260px; padding: 20px; }
}
</style>
