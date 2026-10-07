<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import UiIcon from '@/components/UiIcon.vue'
import AdviceDrawer from '@/components/AdviceDrawer.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'
import MealDialog from '@/components/MealDialog.vue'
import PhotoMealDialog from '@/components/PhotoMealDialog.vue'
import RangeMetric from '@/components/RangeMetric.vue'

const emit = defineEmits<{ openRecords: [] }>()
import {
  api,
  type AdviceCard,
  type Exercise,
  type FollowUpMessage,
  type Meal,
} from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'
import { touchesTarget } from '@/utils/energy'

const store = useQinghengStore()
const mealDialog = ref(false)
const photoDialog = ref(false)
const exerciseDialog = ref(false)
const editingMeal = ref<Meal | null>(null)
const editingExercise = ref<Exercise | null>(null)
const weight = ref(store.profile?.current_weight_kg || 0)
const selectedAdvice = ref<AdviceCard | null>(null)
const conversations = ref<Record<string, FollowUpMessage[]>>({})

const detail = computed(() => store.today)
const newMealIds = ref(new Set<string>())
let previousMealIds = new Set(store.today?.meals.map(meal => meal.id) || [])
let highlightTimer: ReturnType<typeof setTimeout> | undefined
watch(detail, (day) => {
  if (!day) return
  newMealIds.value = new Set(day.meals.filter(meal => !previousMealIds.has(meal.id)).map(meal => meal.id))
  previousMealIds = new Set(day.meals.map(meal => meal.id))
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => { newMealIds.value = new Set() }, 1200)
})
onBeforeUnmount(() => { if (highlightTimer) clearTimeout(highlightTimer) })
const deficitLabel = computed(() => {
  const value = detail.value?.summary.deficit
  if (value && value.high < 0) return '今日热量盈余'
  return '今日热量缺口'
})
const adviceCards = computed(() => store.cachedAdvice?.cards || [])
const scaleMin = -600
const scaleMax = 1000
const scalePosition = (value: number) => Math.min(98, Math.max(2, ((value - scaleMin) / (scaleMax - scaleMin)) * 100))
const overflowLow = computed(() => !!detail.value?.meals.length && detail.value.summary.deficit.low < scaleMin)
const overflowHigh = computed(() => !!detail.value?.meals.length && detail.value.summary.deficit.high > scaleMax)
const formatKcal = (value: number) => value.toLocaleString('zh-CN')
const balanceStyles = computed(() => {
  const summary = detail.value?.summary
  if (!summary) return {}
  const midpoint = (summary.deficit.low + summary.deficit.high) / 2
  const targetStart = scalePosition(summary.target_deficit.low)
  const targetEnd = scalePosition(summary.target_deficit.high)
  return {
    '--balance-position': `${scalePosition(midpoint)}%`,
    '--range-start': `${scalePosition(summary.deficit.low)}%`,
    '--range-width': `${Math.max(0.5, scalePosition(summary.deficit.high) - scalePosition(summary.deficit.low))}%`,
    '--target-start': `${targetStart}%`,
    '--target-width': `${Math.max(3, targetEnd - targetStart)}%`,
  }
})
const deficitTouchesTarget = computed(() => {
  const summary = detail.value?.summary
  return !!summary && touchesTarget(summary.deficit, summary.target_deficit)
})
const balanceNarrative = computed(() => {
  const summary = detail.value?.summary
  if (!summary) return ''
  if (!detail.value?.meals.length) return '记下第一餐，开始了解今天'
  if (summary.deficit.high < 0) return '今天处于能量盈余区间'
  if (deficitTouchesTarget.value) return '今天的区间触及目标'
  if (summary.deficit.high < summary.target_deficit.low) return '今天的缺口低于目标'
  return '今天的缺口高于目标'
})
const balanceDescription = computed(() => {
  const day = detail.value
  if (!day?.meals.length) return '今日能量平衡：尚未记录饮食'
  const { deficit, target_deficit: target } = day.summary
  return `今日能量平衡：缺口估算 ${formatKcal(deficit.low)} 至 ${formatKcal(deficit.high)} 千卡，目标 ${formatKcal(target.low)} 至 ${formatKcal(target.high)} 千卡。${balanceNarrative.value}。刻度范围 ${formatKcal(scaleMin)} 至 ${formatKcal(scaleMax)} 千卡。`
})
const dateLabel = computed(() => {
  const value = detail.value?.summary.record_date
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  return `${date.getMonth() + 1}月${date.getDate()}日 · ${['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]}`
})

function formatTime(value: string) {
  return value.slice(0, 5)
}

function sourceLabel(source: string) {
  return source === 'template' ? '内置模板' : source === 'ai' ? 'AI 估算' : '用户填写'
}

function confidenceLabel(confidence: string | null) {
  return confidence === 'high'
    ? '高置信度'
    : confidence === 'medium'
      ? '中置信度'
      : confidence === 'low'
        ? '低置信度'
        : ''
}

function portionLabel(basis: string | null) {
  const labels: Record<string, string> = {
    count: '按数量',
    container: '按容器',
    package: '按包装',
    geometry: '按形状',
    mixed: '按混合菜',
    visual: '按画面体积',
  }
  return basis ? labels[basis] || '自动估算' : ''
}

function editMeal(meal: Meal) {
  editingMeal.value = meal
  mealDialog.value = true
}

function editExercise(exercise: Exercise) {
  editingExercise.value = exercise
  exerciseDialog.value = true
}

async function removeMeal(meal: Meal) {
  if (!window.confirm(`删除“${meal.display_name}”并重新计算今日缺口？`)) return
  await store.mutate(() => api.deleteMeal(meal.id))
}

async function removeExercise(exercise: Exercise) {
  if (!window.confirm(`删除“${exercise.activity_name}”记录？`)) return
  await store.mutate(() => api.deleteExercise(exercise.id))
}

async function saveWeight() {
  try {
    await store.saveWeight(weight.value)
  } catch {
    // The store displays the save/refresh error in the shared error toast.
  }
}

function closeMealDialog() {
  mealDialog.value = false
  editingMeal.value = null
}

function closeExerciseDialog() {
  exerciseDialog.value = false
  editingExercise.value = null
}

async function generateAdvice() {
  try {
    await store.generateAdvice()
  } catch {
    // The store exposes the API error through the app's error notification.
    // A Vue event handler must consume the rejection after it has been reported.
  }
}

function openAdvice(card: AdviceCard) {
  selectedAdvice.value = card
  if (!conversations.value[card.type]) conversations.value[card.type] = []
}

function updateConversation(messages: FollowUpMessage[]) {
  if (selectedAdvice.value) conversations.value[selectedAdvice.value.type] = messages
}
</script>

<template>
  <main v-if="detail" class="today-page">
    <header class="page-header">
      <div class="header-meta">
        <details class="date-menu">
          <summary class="eyebrow">{{ dateLabel }} <span aria-hidden="true">⌄</span></summary>
          <div><p>当前显示今日记录</p><button @click="emit('openRecords')">查看历史记录 →</button></div>
        </details>

      </div>
      <button class="secondary-action" @click="mealDialog = true"><span>＋</span> 手动记录</button>
    </header>

    <section class="day-overview">
      <header class="overview-heading">
        <div>

          <h1>今天，轻一点。</h1>
        </div>
        <span class="hero-note">三餐四季，<br />都是向更好的自己靠近。</span>
        <svg class="hero-sprig" viewBox="0 0 90 100" aria-hidden="true"><circle cx="66" cy="88" r="32" fill="#f9d1cb"/><path d="M64 68Q60 37 42 17" fill="none" stroke="#91a078" stroke-width="2"/><path d="M56 42Q27 41 25 10Q53 13 56 42Z" fill="#bdc7a3"/><path d="M61 52Q61 22 88 14Q87 43 61 52Z" fill="#819b71"/></svg>
      </header>
      <div class="overview-layout">
        <h2 class="ledger-title"><UiIcon name="chart" /> 能量手账</h2>
        <div class="metrics-grid">
          <RangeMetric
            class="deficit-metric"
            :label="deficitLabel"
            description="缺口 = 全天预计消耗 − 已记录摄入。正数表示缺口，负数表示盈余；未记录的餐食会使当前缺口偏高。"
            :value="detail.summary.deficit"
            :status="!detail.meals.length ? '等待记录' : deficitTouchesTarget ? '触及目标' : detail.summary.deficit.high < detail.summary.target_deficit.low ? '低于目标' : '高于目标'"
            :tone="deficitTouchesTarget ? 'green' : 'orange'"
            :hint="`目标 ${detail.summary.target_deficit.low}–${detail.summary.target_deficit.high} kcal`"
          />
          <RangeMetric icon="meal" label="今日摄入" :value="detail.summary.intake" />
          <RangeMetric
            icon="activity" label="预计消耗"
            :value="detail.summary.total_expenditure"
            tone="neutral"
            :hint="`运动 ${detail.summary.exercise_expenditure.low === detail.summary.exercise_expenditure.high ? detail.summary.exercise_expenditure.low : `${detail.summary.exercise_expenditure.low}–${detail.summary.exercise_expenditure.high}`}`"
          />

        </div>
        <section class="balance-board" :style="balanceStyles">
          <p class="ruler-note">全天预计消耗 − 已记录摄入</p>
          <div class="balance-ruler" :class="{ 'balance-ruler--empty': !detail.meals.length }" role="img" :aria-label="balanceDescription">
            <div v-if="overflowLow || overflowHigh" class="ruler-overflow">
              <div v-if="overflowLow" class="ruler-overflow__low">
                <strong>◂ 下限约 {{ formatKcal(detail.summary.deficit.low) }} kcal</strong>
                <small>低于刻度 {{ formatKcal(scaleMin - detail.summary.deficit.low) }} kcal</small>
              </div>
              <div v-if="overflowHigh" class="ruler-overflow__high">
                <strong>上限约 {{ formatKcal(detail.summary.deficit.high) }} kcal ▸</strong>
                <small>超出刻度 {{ formatKcal(detail.summary.deficit.high - scaleMax) }} kcal</small>
              </div>
            </div>
            <div class="ruler-track">
              <span class="ruler-anchor ruler-anchor--min" aria-hidden="true" />
              <span class="ruler-anchor ruler-anchor--zero" aria-hidden="true" />
              <span class="ruler-anchor ruler-anchor--max" aria-hidden="true" />
              <span class="target-zone"><span class="target-label">目标区间<br />{{ detail.summary.target_deficit.low }}–{{ detail.summary.target_deficit.high }}</span></span><span v-if="detail.meals.length" class="estimate-zone" /><span v-if="detail.meals.length" class="balance-marker" />
            </div>
            <div class="ruler-labels">
              <span>−600</span><span>0</span><span>1,000 kcal</span>
            </div>
          </div>

        </section>
        <button class="capture-button" @click="photoDialog = true"><UiIcon name="camera" /><strong>拍照记录</strong><span>拍下整餐，轻松记一笔。</span></button>
      </div>
    </section>

    <p v-if="!detail.meals.length" class="first-meal-tip">让食物完整入镜，选择餐次后即可入账。也可以使用右上角的手动记录。</p>

    <div v-if="detail.summary.risk_flags.length" class="risk-chip">
      <span>!</span>
      <p>当前档案存在需要留意的健康风险；生成今日建议可查看原因。计算仍可继续。</p>
    </div>

    <section class="content-grid">
      <div class="main-column">
        <section class="panel meals-panel">
          <header class="panel-header">
            <div>

              <h2><UiIcon name="meal" /> 今日餐食</h2>
            </div>
            <span>{{ detail.meals.length }} 餐已记</span>
          </header>
          <TransitionGroup v-if="detail.meals.length" name="meal" tag="div" class="meal-list">
            <article v-for="meal in detail.meals" :key="meal.id" class="meal-card" :class="{ 'meal-card--new': newMealIds.has(meal.id) }">
              <div class="meal-card__top">
                <div class="meal-icon"><UiIcon name="meal" /></div>
                <div class="meal-title">
                  <div>
                    <strong>{{ meal.display_name }}</strong
                    ><span>{{ formatTime(meal.recorded_time) }}</span
                    ><b v-if="meal.entry_method === 'photo'"
                      >AI 拍照 · {{ confidenceLabel(meal.estimate_confidence) }}</b
                    >
                  </div>
                  <p>{{ meal.items.map((item) => item.name).join(' · ') }}</p>
                </div>
                <strong class="meal-kcal"
                  >{{ meal.kcal.low }}–{{ meal.kcal.high }} <small>kcal</small></strong
                >
              </div>
              <details>
                <summary>查看 {{ meal.items.length }} 项组成与来源</summary>
                <div class="component-list">
                  <div v-for="item in meal.items" :key="item.id">
                    <span
                      ><strong>{{ item.name }}</strong
                      ><small
                        >{{
                          item.grams
                            ? `${item.grams.low}–${item.grams.high} 克`
                            : `${item.quantity} ${item.unit}`
                        }}
                        · {{ sourceLabel(item.estimate_source)
                        }}{{
                          item.estimate_confidence
                            ? ` · 综合${confidenceLabel(item.estimate_confidence)}`
                            : ''
                        }}</small
                      ><small v-if="item.portion_detail" class="portion-detail"
                        >{{ portionLabel(item.portion_basis) }}：{{ item.portion_detail }}</small
                      ><small v-if="item.portion_confidence && item.density_confidence"
                        >份量{{ confidenceLabel(item.portion_confidence) }} · 热量密度{{
                          confidenceLabel(item.density_confidence)
                        }}</small
                      ></span
                    ><b>{{ item.kcal.low }}–{{ item.kcal.high }} kcal</b
                    ><em>{{ item.source_version }}</em>
                  </div>
                </div>
              </details>
              <footer>
                <button v-if="meal.editable" @click="editMeal(meal)">编辑</button
                ><button v-if="meal.deletable" class="danger" @click="removeMeal(meal)">
                  删除{{ meal.entry_method === 'photo' ? '重录' : '' }}
                </button>
              </footer>
            </article>
          </TransitionGroup>
          <div v-else class="empty-state">
            <div>餐</div>
            <strong>今天还没有饮食记录</strong>
            <p>拍一张整餐照片，识别结果会自动出现在这里。</p>
            <button @click="photoDialog = true">拍照记录第一餐</button>
            <button class="empty-state__manual" @click="mealDialog = true">改用手动记录</button>
          </div>
        </section>

        <section class="panel">
          <header class="panel-header">
            <div>
              <p class="eyebrow">额外消耗</p>
              <h2>活动记录</h2>
            </div>
            <button class="text-action" @click="exerciseDialog = true">＋ 记录运动</button>
          </header>
          <div v-if="detail.exercises.length" class="exercise-list">
            <article v-for="exercise in detail.exercises" :key="exercise.id">
              <div>
                <strong>{{ exercise.activity_name }}</strong
                ><span
                  >{{ formatTime(exercise.recorded_time) }} · {{ exercise.duration_minutes }} 分钟 ·
                  {{
                    exercise.intensity === 'low'
                      ? '较低'
                      : exercise.intensity === 'high'
                        ? '较高'
                        : '中等'
                  }}</span
                >
              </div>
              <b
                >{{ exercise.kcal.low }}–{{ exercise.kcal.high }} kcal
                <small>{{ exercise.estimate_source === 'met' ? 'MET' : '已修正' }}</small></b
              >
              <div class="row-actions">
                <button @click="editExercise(exercise)">编辑</button
                ><button class="danger" @click="removeExercise(exercise)">删除</button>
              </div>
            </article>
          </div>
          <p v-else class="small-empty">没有运动记录；日常基线仍按静息消耗 × 1.2 计算。</p>
        </section>
      </div>

      <aside class="side-column">
        <section class="panel weight-card">

          <h2>今日体重</h2>
          <div class="weight-input">
            <input v-model.number="weight" type="number" min="30" max="300" step="0.1" /><b>kg</b>
          </div>
          <button :disabled="store.busy" aria-label="保存今日体重" @click="saveWeight">保存</button>
          <small>每天一次，记录身体的小变化。</small>
        </section>

        <section class="panel advice-panel">

          <h2><UiIcon name="leaf" /> 今日建议</h2>
          <template v-if="adviceCards.length">
            <button
              v-for="card in adviceCards"
              :key="card.type"
              class="advice-card"
              @click="openAdvice(card)"
            >
              <span>{{
                card.type === 'status' ? '衡' : card.type === 'next_meal' ? '餐' : '叮'
              }}</span>
              <div>
                <strong>{{ card.title }}</strong>
                <p>{{ card.body }}</p>
              </div>
              <b>›</b>
            </button>
          </template>
          <div v-else class="advice-empty">
            <div>✓</div>
            <p>根据今天的饮食和活动，为下一餐找一点灵感。</p>
            <button :disabled="store.busy" @click="generateAdvice">
              {{ store.busy ? '生成中…' : '生成今日建议' }}
            </button>
            <small>点击后会将今日必要记录发送给 AI 分析。</small>
          </div>
        </section>
      </aside>
    </section>
    <footer class="page-footer"><strong>轻衡 <span>QINGHENG</span></strong><span>记录真实的饮食 · 保持生活的平衡</span><em>轻一点，与生活更好一点。</em></footer>
  </main>
  <main v-else class="today-page" role="status">
    <p>今日数据尚未加载，请刷新后查看。</p>
    <button class="secondary-action" :disabled="store.busy" @click="store.reloadToday()">刷新今日数据</button>
  </main>

  <Transition name="dialog">
  <MealDialog v-if="mealDialog" :meal="editingMeal" @close="closeMealDialog" />
  </Transition>
  <Transition name="dialog">
  <PhotoMealDialog v-if="photoDialog" @close="photoDialog = false" />
  </Transition>
  <Transition name="dialog">
  <ExerciseDialog
    v-if="exerciseDialog"
    :exercise="editingExercise"
    @close="closeExerciseDialog"
  />
  </Transition>
  <Transition name="dialog">
  <AdviceDrawer
    v-if="selectedAdvice"
    :card="selectedAdvice"
    :messages="conversations[selectedAdvice.type] || []"
    @close="selectedAdvice = null"
    @update:messages="updateConversation"
  />
  </Transition>
</template>

<style scoped>

.today-page {
  width: min(1360px, 100%);
  margin: 0 auto;
  padding: 24px 28px 40px;
  max-width: 1240px;
}
.eyebrow {
  margin: 0;
  font-family: var(--qh-data);
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--qh-brand);
  font-size: 12px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 17px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--qh-border);
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 13px;
}
.header-meta > span {
  padding-left: 13px;
  border-left: 1px solid var(--qh-border-strong);
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
  letter-spacing: 0.08em;
}
.secondary-action {
  min-height: 39px;
  padding: 0 14px;
  border: 1px solid var(--qh-border-strong);
  background: rgb(251 253 249 / 82%);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  border-radius: 999px;
  border-color: var(--qh-brand);
}
.secondary-action span {
  margin-right: 3px;
  font-family: var(--qh-data);
}
.secondary-action:hover {
  border-color: var(--qh-green);
  background: white;
}

.day-overview {
  margin-top: 18px;
}
.overview-heading {
  position: relative;
  isolation: isolate;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
}
.overview-heading > span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
}
.overview-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border: 1px solid var(--qh-border);
  border-radius: 16px;
  padding: 18px;
  background: #fffcf8;
}
.balance-board {
  position: relative;
  min-width: 0;
  box-shadow: none;
  border: 0;
  background: transparent;
  border-radius: 0;
  padding: 10px 6px 0;
  overflow: visible;
}
.balance-ruler {
  position: relative;
  z-index: 1;
  margin: 8px 0 0;
}
.ruler-track {
  position: relative;
  height: 10px;
  background: repeating-linear-gradient(90deg, #c8b5ad 0 1px, transparent 1px 5%), linear-gradient(#f8e5df, #f8e5df) center / 100% 6px no-repeat;
  border-bottom: 0;
  margin-top: 46px;
}
.target-zone {
  position: absolute;
  left: var(--target-start);
  width: var(--target-width);
  border: 1px solid var(--qh-green);
  min-width: 0;
  top: -8px;
  height: 26px;
  border-radius: 0;
  background: #b3c69f99;
  border-color: #789264;
}
.balance-marker {
  position: absolute;
  top: 50%;
  left: var(--balance-position);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  background: #d45110;
  border: 1px solid white;
  box-shadow: none;
}
.ruler-labels {
  font-family: var(--qh-data);
  letter-spacing: 0.04em;
  display: block;
  position: relative;
  height: 18px;
  font-size: 12px;
  margin-top: 12px;
  color: var(--qh-text);
}
.ruler-labels span:nth-child(2) {
  text-align: center;
  display: inline;
  left: 37.5%;
  transform: translateX(-50%);
}
.ruler-labels span:last-child {
  text-align: right;
  right: 0;
}
.metrics-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 2.5fr) minmax(0, 1fr);
  align-items: start;
}
.metrics-grid :deep(.metric) {
  border-color: var(--qh-border);
  box-shadow: none;
  background: #fbf5ee;
  border-radius: 14px;
  padding: 18px 14px;
}
.metrics-grid :deep(.deficit-metric) {
  grid-row: span 2;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: var(--qh-sage-soft);
  border-width: 1px;
  padding: 20px 24px;
  border-color: transparent;
}
.metrics-grid :deep(.deficit-metric.metric--orange) {
  background: #ffe1cc;
  border-color: transparent;
}
.metrics-grid :deep(.deficit-metric .metric__value) {
  flex-wrap: wrap;
}
.metrics-grid :deep(.deficit-metric .metric__value strong) {
  font-size: clamp(32px, 3.7vw, 52px);
  letter-spacing: -0.045em;
}
.metrics-grid :deep(.deficit-metric.metric--orange strong) {
  color: var(--qh-text);
}

.risk-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 11px 14px;
  border: 1px solid #edbd98;
  border-radius: 15px 5px 15px 5px;
  color: #75491f;
  background: #fff5e9;
  font-size: 13px;
}
.risk-chip span {
  display: grid;
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  color: white;
  background: var(--qh-orange);
  font-weight: 900;
}
.risk-chip p {
  margin: 0;
}
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 1fr);
  gap: 14px;
  margin-top: 14px;
}
.main-column {
  display: grid;
  align-content: start;
  gap: 18px;
}
.side-column {
  display: grid;
  align-content: start;
  gap: 18px;
}
.panel {
  overflow: hidden;
  border: 1px solid var(--qh-border);
  box-shadow: var(--qh-shadow-soft);
  border-radius: 16px;
  background: #fffcf8;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--qh-border);
  padding: 18px 20px 12px;
}
.panel-header h2 {
  margin: 4px 0 0;
  font-size: 22px;
  letter-spacing: -0.025em;
}
.weight-card h2 {
  margin: 4px 0 0;
  letter-spacing: -0.025em;
  font-size: 16px;
}
.advice-panel h2 {
  margin: 4px 0 0;
  font-size: 22px;
  letter-spacing: -0.025em;
}
.panel-header > span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
}
.text-action {
  border: 0;
  background: transparent;
  font-weight: 800;
  cursor: pointer;
  color: var(--qh-brand);
  min-height: 44px;
}
.text-action:hover {
  color: var(--qh-orange-dark);
}
.meal-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  padding: 0 12px 12px;
}
.meal-card {
  min-width: 0;
  position: relative;
  padding: 24px 0;
  border: 0;
  border-bottom: 1px solid var(--qh-border);
  border-radius: 0;
  background: transparent;
}
.meal-card--new { outline: 2px solid var(--qh-brand-soft); outline-offset: 4px; }
.meal-card__top {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 13px;
  align-items: start;
}
.meal-icon {
  display: grid;
  place-items: center;
  border: 0;
  gap: 12px;
  font-family: var(--qh-data);
  font-size: 12px;
  font-weight: 400;
  color: var(--qh-brand);
  background: #f3e8dc;
  border-radius: 12px;
  width: 52px;
  height: 52px;
}
.meal-title > div {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}
.meal-title span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
}
.meal-title b {
  padding: 3px 6px;
  border-radius: 6px;
  color: var(--qh-orange-dark);
  background: var(--qh-orange-soft);
  font-size: 12px;
}
.meal-title p {
  margin: 6px 0 0;
  overflow: hidden;
  color: var(--qh-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  line-height: 1.8;
  white-space: normal;
  overflow-wrap: anywhere;
}
.meal-kcal {
  color: var(--qh-green-dark);
  font-family: var(--qh-data);
  font-size: 14px;
  white-space: nowrap;
}
.meal-kcal small {
  font-size: 12px;
  letter-spacing: 0.05em;
}
details {
  margin-top: 13px;
  border-top: 1px solid var(--qh-border);
}
summary {
  padding-top: 11px;
  color: var(--qh-muted);
  font-size: 11px;
  cursor: pointer;
}
summary:hover {
  color: var(--qh-green-dark);
}
.component-list {
  margin-top: 7px;
}
.component-list > div {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 3px 8px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--qh-border);
}
.component-list span {
  display: grid;
  gap: 2px;
}
.component-list small {
  color: var(--qh-muted);
  font-size: 12px;
  font-style: normal;
}
.component-list em {
  color: var(--qh-muted);
  font-size: 12px;
  font-style: normal;
  grid-column: 1 / -1;
  font-family: var(--qh-data);
}
.component-list .portion-detail {
  color: var(--qh-green-dark);
  line-height: 1.4;
}
.component-list b {
  font-family: var(--qh-data);
  font-size: 12px;
}
.meal-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
  margin-left: 65px;
}
.meal-card footer button {
  border: 1px solid var(--qh-border-strong);
  border-radius: 999px;
  padding: 0 18px;
  color: var(--qh-text);
  background: #fffcf8;
  font-size: 12px;
  cursor: pointer;
  min-height: 36px;
}
.row-actions button {
  border: 0;
  color: var(--qh-green-dark);
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}
.danger {
  color: #a24a3f !important;
}
.empty-state {
  display: grid;
  place-items: center;
  padding: 52px 20px;
  text-align: center;
}
.empty-state > div {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid #c5d8ca;
  border-radius: 50%;
  color: var(--qh-green-dark);
  background: var(--qh-sage-soft);
  font-family: var(--qh-display);
  font-weight: 800;
}
.empty-state strong {
  margin-top: 13px;
}
.empty-state p {
  color: var(--qh-muted);
  font-size: 12px;
}
.small-empty {
  color: var(--qh-muted);
  font-size: 12px;
  margin: 0;
  padding: 24px;
}
.empty-state button {
  margin-top: 10px;
  padding: 10px 15px;
  border: 0;
  border-radius: 12px;
  color: white;
  background: var(--qh-green);
  font-weight: 700;
  cursor: pointer;
}
.empty-state .empty-state__manual {
  margin-top: 5px;
  padding: 6px 10px;
  color: var(--qh-muted);
  background: transparent;
  font-size: 11px;
}
.empty-state .empty-state__manual:hover {
  color: var(--qh-green-dark);
}
.exercise-list {
  padding: 4px 22px 12px;
}
.exercise-list article {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 15px;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--qh-border);
}
.exercise-list article:last-child {
  border-bottom: 0;
}
.exercise-list article > div:first-child {
  display: grid;
  gap: 4px;
}
.exercise-list span {
  color: var(--qh-muted);
  font-size: 12px;
}
.exercise-list small {
  color: var(--qh-muted);
  font-size: 12px;
}
.exercise-list b {
  color: var(--qh-orange-dark);
  font-family: var(--qh-data);
  font-size: 12px;
}
.row-actions {
  display: flex;
}
.weight-card {
  position: relative;
  background: var(--qh-card);
  display: grid;
  grid-template-columns: auto minmax(90px, 1fr) auto;
  gap: 12px;
  padding: 16px;
  align-items: center;
}
.advice-panel {
  padding: 18px;
}
.weight-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 54px;
  height: 4px;
  content: '';
  background: var(--qh-brand-soft);
  display: none;
}
.weight-input {
  position: relative;
  margin-top: 18px;
  margin: 0;
}
.weight-input input {
  width: 100%;
  padding: 0 52px 0 14px;
  border: 1px solid var(--qh-border-strong);
  color: var(--qh-text);
  background: white;
  font-family: var(--qh-data);
  font-weight: 800;
  height: 42px;
  font-size: 20px;
  border-radius: 10px;
}
.weight-input b {
  position: absolute;
  right: 14px;
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 11px;
  top: 13px;
}
.weight-card > button {
  width: 100%;
  margin-top: 10px;
  border: 0;
  color: white;
  font-weight: 800;
  cursor: pointer;
  background: var(--qh-brand);
  border-radius: 12px;
  margin: 0;
  padding: 0 14px;
  min-height: 40px;
}
.weight-card > button:hover {
  background: var(--qh-green);
}
.advice-empty button:hover {
  background: var(--qh-green);
}
.weight-card > small {
  display: block;
  margin-top: 10px;
  color: var(--qh-muted);
  line-height: 1.5;
  grid-column: 1 / -1;
  margin: 0;
  font-size: 12px;
}
.advice-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 11px;
  width: 100%;
  margin-top: 11px;
  padding: 13px;
  border: 1px solid var(--qh-border);
  border-radius: 14px 5px 14px 5px;
  text-align: left;
  background: white;
  cursor: pointer;
}
.advice-card:hover {
  border-color: var(--qh-green);
  transform: translateX(2px);
}
.advice-card > span {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  color: var(--qh-green-dark);
  background: var(--qh-sage-soft);
  font-family: var(--qh-data);
  font-size: 12px;
  font-weight: 900;
}
.advice-card > div {
  min-width: 0;
}
.advice-card p {
  display: -webkit-box;
  margin: 4px 0 0;
  overflow: hidden;
  color: var(--qh-muted);
  font-size: 11px;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.advice-card > b {
  color: var(--qh-muted);
  font-size: 20px;
}
.advice-empty {
  display: grid;
  padding-top: 10px;
  text-align: left;
  place-items: start;
}
.advice-empty > div {
  width: 50px;
  height: 50px;
  place-items: center;
  border: 1px solid #c5d8ca;
  border-radius: 50%;
  color: var(--qh-green-dark);
  background: var(--qh-sage-soft);
  font-size: 20px;
  display: none;
}
.advice-empty strong {
  margin-top: 12px;
  font-size: 12px;
  margin: 0;
  color: var(--qh-muted);
}
.advice-empty p {
  margin: 7px 0 13px;
  color: var(--qh-muted);
  font-size: 12px;
  line-height: 1.55;
}
.advice-empty button {
  width: 100%;
  min-height: 43px;
  border: 0;
  font-weight: 800;
  cursor: pointer;
  border-radius: 12px;
  background: #f5e8d6;
  color: var(--qh-text);
}
.overview-heading h1 {
  letter-spacing: 0.02em;
  font-size: clamp(28px, 3vw, 40px);
  margin: 0;
}
.ruler-overflow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  color: var(--qh-orange-dark);
  margin-bottom: 18px;
  min-height: 40px;
}
.ruler-overflow > div {
  display: grid;
  gap: 4px;
  overflow-wrap: anywhere;
}
.ruler-overflow strong {
  font-size: 13px;
  font-weight: 700;
}
.ruler-overflow small {
  font-size: 12px;
}
.ruler-overflow__low {
  grid-column: 1;
}
.ruler-overflow__high {
  grid-column: 2;
  text-align: right;
}
.ruler-anchor {
  position: absolute;
  z-index: 1;
  pointer-events: none;
  height: 18px;
  width: 1px;
  top: -4px;
  background: #816e75;
}
.ruler-anchor--min {
  left: 0;
}
.ruler-anchor--zero {
  left: 37.5%;
  transform: translateX(-50%);
}
.ruler-anchor--max {
  right: 0;
}
.estimate-zone {
  position: absolute;
  left: var(--range-start);
  width: var(--range-width);
  border-radius: 4px;
  top: 3px;
  height: 4px;
  background: #d45110;
}
.ruler-labels span {
  position: absolute;
  top: 0;
}
.ruler-labels span:first-child {
  left: 0;
}
.ruler-note {
  color: var(--qh-muted);
  line-height: 1.6;
  margin: 0;
  font-size: 13px;
}
.capture-button {
  align-items: center;
  padding: 0 22px;
  border: 0;
  cursor: pointer;
  display: flex;
  justify-content: center;
  gap: 12px;
  width: 92%;
  margin: 24px auto 2px;
  min-height: 54px;
  background: var(--qh-brand);
  color: white;
  border-radius: 999px;
}
.capture-button:hover {
  background: #3a001d;
}
.first-meal-tip {
  margin: 10px 4px 0;
  font-size: 12px;
  color: var(--qh-muted);
  line-height: 1.7;
}
.meal-card:last-child {
  border-bottom: 0;
}
.meal-icon i {
  display: block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--qh-brand);
  box-shadow: 0 0 0 5px var(--qh-brand-soft);
}
.meal-card summary {
  font-size: 12px;
  padding-block: 10px;
  cursor: pointer;
}
.meal-card details {
  margin-left: 65px;
}
.header-meta .eyebrow {
  font-size: 16px;
  letter-spacing: 0;
}
.hero-note {
  line-height: 1.7;
  padding-right: 72px;
}
.hero-sprig { position: absolute; right: -18px; bottom: -30px; width: 82px; height: 92px; z-index: -1; opacity: .8; pointer-events: none; }
.ledger-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
  font-size: 19px;
}
.metrics-grid :deep(.metric::after) {
  display: none;
}
.metrics-grid :deep(.metric__foot) {
  display: none;
}
.metrics-grid :deep(.metric__head small) {
  display: none;
}
.metrics-grid :deep(.metric strong) {
  font-family: var(--qh-numeral);
  font-size: clamp(20px, 2vw, 28px);
  letter-spacing: -0.04em;
}
.metrics-grid :deep(.deficit-metric .metric__foot) {
  display: flex;
  margin-top: 8px;
  font-size: 15px;
  color: var(--qh-text);
  letter-spacing: 0;
}
.metrics-grid :deep(.deficit-metric .metric__status) {
  position: absolute;
  right: 20px;
  top: 17px;
  background: #b6440a;
  color: white;
  font-weight: 500;
}
.metrics-grid :deep(.deficit-metric.metric--green .metric__status) {
  background: var(--qh-green);
}
.ruler-overflow + .ruler-track {
  margin-top: 0;
}
.target-label {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 12px;
  color: #416d47;
  text-align: center;
}
.capture-button strong {
  font-size: 19px;
  font-weight: 500;
}
.capture-button > span {
  border-left: 1px solid #d8b7c5;
  padding-left: 24px;
  margin-left: 12px;
  font-size: 14px;
}
.date-menu { position: relative; margin: 0; border: 0; z-index: 5; }
.date-menu > summary { list-style: none; padding: 4px 0; cursor: pointer; }
.date-menu > summary::-webkit-details-marker { display: none; }
.date-menu > div { position: absolute; top: 100%; left: 0; width: 210px; padding: 14px; background: var(--qh-card); border: 1px solid var(--qh-border); border-radius: 12px; box-shadow: var(--qh-shadow-soft); }
.date-menu p { margin: 0 0 12px; font-size: 12px; color: var(--qh-muted); }
.date-menu button { border: 0; background: var(--qh-brand-soft); padding: 10px 12px; border-radius: 8px; cursor: pointer; }
.page-footer { display: flex; align-items: center; flex-wrap: wrap; gap: 18px; padding: 26px 0 4px; margin-top: 20px; border-top: 1px solid var(--qh-border); font-size: 12px; color: var(--qh-muted); }
.page-footer strong { color: var(--qh-brand); font-family: var(--qh-display); }
.page-footer strong span { font: 10px var(--qh-body); letter-spacing: .14em; margin-left: 12px; }
.page-footer em { margin-left: auto; font: 15px var(--qh-display); }
.advice-empty small { margin-top: 10px; font-size: 12px; line-height: 1.6; color: var(--qh-muted); }
@media (prefers-reduced-motion: no-preference) {
  .meal-card--new { animation: meal-added 400ms ease; }
  details[open] .component-list { animation: detail-reveal 200ms ease; }
  @keyframes detail-reveal { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
}
@media (prefers-reduced-motion: no-preference) {
  .day-overview {
    animation: settle-in 500ms 70ms ease both;
  }
  @keyframes settle-in {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .balance-marker {
    transition:
      left 400ms ease,
      width 400ms ease;
  }
  .estimate-zone {
    transition:
      left 400ms ease,
      width 400ms ease;
  }
}
@media (max-width: 1100px) {
  .content-grid {
    grid-template-columns: minmax(0, 1.2fr) minmax(280px, 1fr);
  }
  .side-column {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .hero-note { padding-right: 40px; }
  .hero-sprig { width: 65px; height: 75px; right: -10px; }
  .balance-ruler { display: flex; flex-direction: column; }
  .ruler-track { order: 1; }
  .ruler-labels { order: 2; }
  .ruler-overflow { order: 3; margin-top: 8px; }
  .today-page {
    padding: 22px 12px calc(104px + env(safe-area-inset-bottom));
  }
  .balance-board {
    padding: 12px 4px 0;
  }
  .metrics-grid {
    gap: 8px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .side-column {
    grid-template-columns: 1fr;
  }
  .exercise-list article {
    grid-template-columns: 1fr auto;
  }
  .row-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
  .day-overview {
    margin-top: 20px;
  }
  .overview-heading {
    gap: 12px;
  }
  .overview-heading > span {
    white-space: normal;
  }
  .metrics-grid :deep(.metric) {
    align-items: center;
    display: block;
    padding: 14px 12px;
  }
  .metrics-grid :deep(.metric__head) {
    display: grid;
    gap: 5px;
  }
  .metrics-grid :deep(.deficit-metric .metric__head) { display: flex; justify-content: flex-start; gap: 8px; }
  .metrics-grid :deep(.metric__value) {
    margin: 12px 0 0;
  }
  .metrics-grid :deep(.metric__foot) {
    display: none;
  }
  .metrics-grid :deep(.deficit-metric) {
    grid-row: auto;
    display: block;
    padding: 18px 16px;
    grid-column: 1 / -1;
  }
  .metrics-grid :deep(.deficit-metric .metric__value) {
    margin-top: 12px;
  }
  .capture-button {
    flex-shrink: 0;
    min-height: 46px;
    font-size: 14px;
    width: 100%;
    gap: 8px;
    padding: 0 12px;
    margin-top: 20px;
  }
  .meal-list {
    padding: 0 16px;
  }
  .meal-card__top {
    gap: 10px;
  }
  .meal-card details {
    margin-left: 62px;
  }
  .meal-card footer {
    margin-left: 62px;
  }
  .overview-layout {
    padding: 12px;
  }
  .metrics-grid :deep(.metric strong) {
    font-size: clamp(18px, 5vw, 26px);
  }
  .metrics-grid :deep(.deficit-metric .metric__value strong) {
    font-size: clamp(28px, 8vw, 38px);
  }
  .metrics-grid :deep(.deficit-metric .metric__foot) {
    display: flex;
    font-size: 13px;
  }
  .content-grid {
    grid-template-columns: 1fr;
  }
  .capture-button strong {
    font-size: 16px;
    white-space: nowrap;
  }
  .capture-button > span {
    font-size: 11px;
    padding-left: 10px;
    margin-left: 0;
  }
  .hero-note br {
    display: none;
  }
  .metrics-grid :deep(.deficit-metric .metric__status) {
    right: 12px;
    top: 14px;
    font-size: 11px;
    padding: 4px 8px;
  }
  .ruler-overflow {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .ruler-overflow__high {
    margin-left: auto;
  }
  .ruler-track {
    margin-top: 48px;
  }
  .ruler-overflow + .ruler-track {
    margin-top: 44px;
  }
}
@media (max-width: 520px) {
  .metrics-grid :deep(.metric:not(.deficit-metric) .metric__value) { gap: 4px; }
  .metrics-grid :deep(.metric:not(.deficit-metric) strong) { font-size: 18px; }
  .metrics-grid :deep(.metric:not(.deficit-metric) em) { font-size: 10px; letter-spacing: 0; }
  .overview-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-meta > span {
    display: none;
  }
  .secondary-action {
    min-height: 36px;
    padding: 0 11px;
  }
  .ruler-labels span:nth-child(2) {
    display: inline;
  }
  .meal-card__top {
    grid-template-columns: auto 1fr;
  }
  .meal-kcal {
    grid-column: 2;
  }
  .panel-header {
    padding: 16px;
  }
}

</style>
