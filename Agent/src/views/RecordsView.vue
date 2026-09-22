<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import RangeMetric from '@/components/RangeMetric.vue'
import { api, type DayDetail } from '@/api/qingheng'

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

function formatTime(value: string) {
  return value.slice(0, 5)
}

function confidenceLabel(confidence: string | null) {
  return confidence === 'high' ? '高置信度' : confidence === 'medium' ? '中置信度' : confidence === 'low' ? '低置信度' : ''
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
      <div><p class="eyebrow">每日手账</p><h1>记录</h1><span>翻到某一天，看看吃过什么、做过什么。</span></div>
      <label class="month-picker"><span>选择月份</span><input v-model="month" type="month" :max="currentMonth" /></label>
    </header>

    <p v-if="localError" class="form-error">{{ localError }}</p>
    <section class="records-layout">
      <aside class="date-list panel">
        <header><strong>{{ month.replace('-', ' 年 ') }} 月</strong><small>{{ dates.length }} 个记录日</small></header>
        <button v-for="value in dates" :key="value" :class="{ active: selectedDate === value }" @click="selectDate(value)"><span>{{ formatDate(value) }}</span><b>{{ value }}</b></button>
        <div v-if="!dates.length && !loading" class="empty-dates">这个月还没有记录</div>
      </aside>

      <div v-if="detail" class="day-detail">
        <header class="day-heading"><div><p class="eyebrow">{{ selectedDate }}</p><h2>{{ formatDate(selectedDate) }}的记录</h2></div><span class="readonly-badge">{{ selectedDate === currentDate ? '今日可修改' : '历史只读' }}</span></header>
        <section class="metrics-grid"><RangeMetric label="摄入" :value="detail.summary.intake" /><RangeMetric label="消耗" :value="detail.summary.total_expenditure" tone="orange" /><RangeMetric label="缺口 / 盈余" :value="detail.summary.deficit" :tone="detail.summary.deficit.high < 0 ? 'orange' : 'green'" /></section>

        <section class="panel detail-panel">
          <header><div><p class="eyebrow">整餐记录</p><h3>饮食</h3></div><span>{{ detail.meals.length }} 餐</span></header>
          <article v-for="meal in detail.meals" :key="meal.id" class="history-row">
            <div><strong>{{ meal.display_name }}</strong><span>{{ formatTime(meal.recorded_time) }} · {{ meal.entry_method === 'photo' ? `AI 拍照 · ${confidenceLabel(meal.estimate_confidence)}` : '手动记录' }}</span><p>{{ meal.items.map((item) => item.name).join(' · ') }}</p></div><b>{{ meal.kcal.low }}–{{ meal.kcal.high }} kcal</b>
          </article>
          <p v-if="!detail.meals.length" class="empty-copy">当天没有饮食记录。</p>
        </section>

        <section class="two-panels">
          <section class="panel detail-panel"><header><div><p class="eyebrow">运动</p><h3>额外消耗</h3></div></header><article v-for="exercise in detail.exercises" :key="exercise.id" class="history-row"><div><strong>{{ exercise.activity_name }}</strong><span>{{ exercise.duration_minutes }} 分钟 · {{ formatTime(exercise.recorded_time) }}</span></div><b>{{ exercise.kcal.low }}–{{ exercise.kcal.high }} kcal</b></article><p v-if="!detail.exercises.length" class="empty-copy">当天没有运动记录。</p></section>
          <section class="panel weight-history"><p class="eyebrow">每日体重</p><strong>{{ detail.weight ? `${detail.weight.weight_kg} kg` : '未记录' }}</strong><span>当天记录的体重</span></section>
        </section>
      </div>

      <section v-else-if="loading" class="no-selection panel" role="status">正在加载记录…</section>
      <section v-else-if="!localError" class="no-selection panel"><div>记</div><strong>没有可查看的日期</strong><p>从今日页开始记录后，日期会出现在这里。</p></section>
    </section>
  </main>
</template>

<style scoped>
.records-page { width: min(1260px, 100%); margin: 0 auto; padding: 34px; }.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }.page-header h1 { margin: 3px 0 5px; font-size: 34px; letter-spacing: -.05em; }.page-header > div > span { color: var(--qh-muted); }.eyebrow { margin: 0; color: var(--qh-green-dark); font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.month-picker { display: grid; gap: 6px; color: var(--qh-muted); font-size: 12px; font-weight: 700; }.month-picker input { height: 42px; padding: 0 11px; border: 1px solid var(--qh-border-strong); border-radius: 11px; background: white; }
.form-error { padding: 11px 13px; border-radius: 11px; color: #8f3f35; background: #fff0ed; }.records-layout { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 18px; }.panel { border: 1px solid var(--qh-border); border-radius: 20px; background: var(--qh-card); box-shadow: var(--qh-shadow-soft); }
.date-list { align-self: start; overflow: hidden; }.date-list header { display: grid; gap: 3px; padding: 18px; border-bottom: 1px solid var(--qh-border); }.date-list header small { color: var(--qh-muted); }.date-list button { display: grid; gap: 3px; width: 100%; padding: 13px 18px; border: 0; border-bottom: 1px solid var(--qh-border); text-align: left; color: var(--qh-text); background: transparent; cursor: pointer; }.date-list button b { color: var(--qh-muted); font-size: 12px; }.date-list button.active { color: var(--qh-green-dark); background: var(--qh-sage-soft); }.empty-dates { padding: 30px 18px; color: var(--qh-muted); font-size: 12px; text-align: center; }
.day-detail { min-width: 0; }.day-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }.day-heading h2 { margin: 4px 0 0; font-size: 24px; }.readonly-badge { padding: 6px 9px; border-radius: 8px; color: var(--qh-muted); background: var(--qh-ivory-strong); font-size: 12px; }.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.detail-panel { margin-top: 15px; padding: 0 20px 8px; }.detail-panel > header { display: flex; align-items: center; justify-content: space-between; padding: 18px 0; border-bottom: 1px solid var(--qh-border); }.detail-panel h3 { margin: 3px 0 0; }.detail-panel header > span { color: var(--qh-muted); font-size: 12px; }.history-row { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: center; padding: 15px 0; border-bottom: 1px solid var(--qh-border); }.history-row:last-child { border-bottom: 0; }.history-row > div { display: grid; gap: 4px; }.history-row span, .history-row p { margin: 0; color: var(--qh-muted); font-size: 12px; }.history-row > b { color: var(--qh-green-dark); }.empty-copy { color: var(--qh-muted); font-size: 12px; }
.two-panels { display: grid; grid-template-columns: 1fr 250px; gap: 15px; }.weight-history { display: grid; align-content: start; margin-top: 15px; padding: 20px; }.weight-history > strong { margin-top: 18px; font-size: 28px; }.weight-history > span { margin-top: 8px; color: var(--qh-muted); font-size: 12px; line-height: 1.5; }.no-selection { display: grid; min-height: 360px; place-items: center; align-content: center; text-align: center; }.no-selection > div { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 16px; color: var(--qh-green-dark); background: var(--qh-sage-soft); }.no-selection strong { margin-top: 12px; }.no-selection p { color: var(--qh-muted); font-size: 12px; }
@media (max-width: 850px) { .records-page { padding: 20px 16px 96px; }.records-layout { grid-template-columns: 1fr; }.date-list { display: flex; overflow-x: auto; }.date-list header { min-width: 160px; }.date-list button { min-width: 125px; border-right: 1px solid var(--qh-border); }.metrics-grid { grid-template-columns: 1fr; }.two-panels { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .page-header { align-items: stretch; flex-direction: column; }.month-picker input { width: 100%; } }
</style>
