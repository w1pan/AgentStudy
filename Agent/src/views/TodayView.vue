<script setup lang="ts">
import { computed, ref } from 'vue'

import AdviceDrawer from '@/components/AdviceDrawer.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'
import MealDialog from '@/components/MealDialog.vue'
import PhotoMealDialog from '@/components/PhotoMealDialog.vue'
import RangeMetric from '@/components/RangeMetric.vue'
import { api, type AdviceCard, type Exercise, type FollowUpMessage, type Meal } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

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
const deficitLabel = computed(() => {
  const value = detail.value?.summary.deficit
  if (value && value.high < 0) return '今日热量盈余'
  return '今日热量缺口'
})
const adviceCards = computed(() => store.cachedAdvice?.cards || [])

function formatTime(value: string) {
  return value.slice(0, 5)
}

function sourceLabel(source: string) {
  return source === 'template' ? '内置模板' : source === 'ai' ? 'AI 估算' : '用户填写'
}

function confidenceLabel(confidence: string | null) {
  return confidence === 'high' ? '高置信度' : confidence === 'medium' ? '中置信度' : confidence === 'low' ? '低置信度' : ''
}

function portionLabel(basis: string | null) {
  const labels: Record<string, string> = {
    count: '按数量', container: '按容器', package: '按包装',
    geometry: '按形状', mixed: '按混合菜', visual: '按画面体积',
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
  await store.mutate(() => api.upsertWeight(weight.value))
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
  await store.generateAdvice()
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
      <div><p class="eyebrow">{{ detail.summary.record_date }}</p><h1>今日</h1><span>用区间记录真实生活，不追求虚假的精确。</span></div>
      <div class="header-actions"><button class="secondary-action" @click="mealDialog = true">＋ 手动记录</button><button class="primary-action" @click="photoDialog = true">▣ 拍照估算</button></div>
    </header>

    <section class="metrics-grid">
      <RangeMetric label="今日摄入" :value="detail.summary.intake" />
      <RangeMetric label="预计消耗" :value="detail.summary.total_expenditure" tone="orange" :hint="`运动 ${detail.summary.exercise_expenditure.low === detail.summary.exercise_expenditure.high ? detail.summary.exercise_expenditure.low : `${detail.summary.exercise_expenditure.low}–${detail.summary.exercise_expenditure.high}`}`" />
      <RangeMetric :label="deficitLabel" :value="detail.summary.deficit" :tone="detail.summary.deficit.high < 0 ? 'orange' : 'green'" :hint="`目标 ${detail.summary.target_deficit.low}–${detail.summary.target_deficit.high}`" />
    </section>

    <div v-if="detail.summary.risk_flags.length" class="risk-chip"><span>!</span><p>当前档案存在需要留意的健康风险；生成今日建议可查看原因。计算仍可继续。</p></div>

    <section class="content-grid">
      <div class="main-column">
        <section class="panel meals-panel">
          <header class="panel-header"><div><p class="eyebrow">今日记录</p><h2>饮食</h2></div><span>{{ detail.meals.length }} 餐</span></header>
          <div v-if="detail.meals.length" class="meal-list">
            <article v-for="meal in detail.meals" :key="meal.id" class="meal-card">
              <div class="meal-card__top">
                <div class="meal-icon">{{ meal.entry_method === 'photo' ? '▣' : '餐' }}</div>
                <div class="meal-title"><div><strong>{{ meal.display_name }}</strong><span>{{ formatTime(meal.recorded_time) }}</span><b v-if="meal.entry_method === 'photo'">AI 拍照 · {{ confidenceLabel(meal.estimate_confidence) }}</b></div><p>{{ meal.items.map((item) => item.name).join(' · ') }}</p></div>
                <strong class="meal-kcal">{{ meal.kcal.low }}–{{ meal.kcal.high }} <small>kcal</small></strong>
              </div>
              <details>
                <summary>查看 {{ meal.items.length }} 项组成与来源</summary>
                <div class="component-list">
                  <div v-for="item in meal.items" :key="item.id"><span><strong>{{ item.name }}</strong><small>{{ item.grams ? `${item.grams.low}–${item.grams.high} 克` : `${item.quantity} ${item.unit}` }} · {{ sourceLabel(item.estimate_source) }}{{ item.estimate_confidence ? ` · 综合${confidenceLabel(item.estimate_confidence)}` : '' }}</small><small v-if="item.portion_detail" class="portion-detail">{{ portionLabel(item.portion_basis) }}：{{ item.portion_detail }}</small><small v-if="item.portion_confidence && item.density_confidence">份量{{ confidenceLabel(item.portion_confidence) }} · 热量密度{{ confidenceLabel(item.density_confidence) }}</small></span><b>{{ item.kcal.low }}–{{ item.kcal.high }} kcal</b><em>{{ item.source_version }}</em></div>
                </div>
              </details>
              <footer><button v-if="meal.editable" @click="editMeal(meal)">编辑</button><button v-if="meal.deletable" class="danger" @click="removeMeal(meal)">删除{{ meal.entry_method === 'photo' ? '重录' : '' }}</button></footer>
            </article>
          </div>
          <div v-else class="empty-state"><div>餐</div><strong>今天还没有饮食记录</strong><p>手动组合模板，或上传一张整餐照片。</p><button @click="mealDialog = true">添加第一餐</button></div>
        </section>

        <section class="panel">
          <header class="panel-header"><div><p class="eyebrow">额外消耗</p><h2>运动</h2></div><button class="text-action" @click="exerciseDialog = true">＋ 记录运动</button></header>
          <div v-if="detail.exercises.length" class="exercise-list">
            <article v-for="exercise in detail.exercises" :key="exercise.id"><div><strong>{{ exercise.activity_name }}</strong><span>{{ formatTime(exercise.recorded_time) }} · {{ exercise.duration_minutes }} 分钟 · {{ exercise.intensity === 'low' ? '较低' : exercise.intensity === 'high' ? '较高' : '中等' }}</span></div><b>{{ exercise.kcal.low }}–{{ exercise.kcal.high }} kcal <small>{{ exercise.estimate_source === 'met' ? 'MET' : '已修正' }}</small></b><div class="row-actions"><button @click="editExercise(exercise)">编辑</button><button class="danger" @click="removeExercise(exercise)">删除</button></div></article>
          </div>
          <p v-else class="small-empty">没有运动记录；日常基线仍按静息消耗 × 1.2 计算。</p>
        </section>
      </div>

      <aside class="side-column">
        <section class="panel weight-card">
          <p class="eyebrow">每日一次</p><h2>今日体重</h2>
          <div class="weight-input"><input v-model.number="weight" type="number" min="30" max="300" step="0.1" /><b>kg</b></div>
          <button :disabled="store.busy" @click="saveWeight">更新体重与基线</button>
          <small>历史记录只读，不绘制趋势图。</small>
        </section>

        <section class="panel advice-panel">
          <p class="eyebrow">按需生成</p><h2>今日建议</h2>
          <template v-if="adviceCards.length">
            <button v-for="card in adviceCards" :key="card.type" class="advice-card" @click="openAdvice(card)"><span>{{ card.type === 'status' ? '01' : card.type === 'next_meal' ? '02' : '03' }}</span><div><strong>{{ card.title }}</strong><p>{{ card.body }}</p></div><b>›</b></button>
          </template>
          <div v-else class="advice-empty"><div>✓</div><strong>数据不会自动发送给 AI</strong><p>点击后仅分析今天，并使用服务端已计算的热量事实。</p><button :disabled="store.busy" @click="generateAdvice">{{ store.busy ? '生成中…' : '生成今日建议' }}</button></div>
        </section>
      </aside>
    </section>

    <MealDialog v-if="mealDialog" :meal="editingMeal" @close="closeMealDialog" />
    <PhotoMealDialog v-if="photoDialog" @close="photoDialog = false" />
    <ExerciseDialog v-if="exerciseDialog" :exercise="editingExercise" @close="closeExerciseDialog" />
    <AdviceDrawer v-if="selectedAdvice" :card="selectedAdvice" :messages="conversations[selectedAdvice.type] || []" @close="selectedAdvice = null" @update:messages="updateConversation" />
  </main>
</template>

<style scoped>
.today-page { width: min(1320px, 100%); margin: 0 auto; padding: 34px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 25px; }.page-header h1 { margin: 3px 0 5px; font-size: 34px; letter-spacing: -.05em; }.page-header span { color: var(--qh-muted); }.eyebrow { margin: 0; color: var(--qh-green-dark); font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.header-actions { display: flex; gap: 10px; }.header-actions button { min-height: 43px; padding: 0 17px; border-radius: 12px; font-weight: 800; cursor: pointer; }.secondary-action { border: 1px solid var(--qh-border); background: white; }.primary-action { border: 0; color: white; background: var(--qh-green); }
.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
.risk-chip { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 11px 14px; border: 1px solid #efc5a0; border-radius: 13px; color: #75491f; background: #fff7ec; font-size: 13px; }.risk-chip span { display: grid; flex: 0 0 24px; width: 24px; height: 24px; place-items: center; border-radius: 50%; color: white; background: var(--qh-orange); font-weight: 900; }.risk-chip p { margin: 0; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 18px; margin-top: 18px; }.main-column, .side-column { display: grid; align-content: start; gap: 18px; }
.panel { border: 1px solid var(--qh-border); border-radius: 20px; background: var(--qh-card); box-shadow: var(--qh-shadow-soft); }.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 22px; border-bottom: 1px solid var(--qh-border); }.panel-header h2, .weight-card h2, .advice-panel h2 { margin: 3px 0 0; font-size: 20px; }.panel-header > span { color: var(--qh-muted); font-size: 12px; }.text-action { border: 0; color: var(--qh-green-dark); background: transparent; font-weight: 800; cursor: pointer; }
.meal-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 13px; padding: 15px; }.meal-card { min-width: 0; padding: 15px; border: 1px solid var(--qh-border); border-radius: 16px; background: #fff; }.meal-card__top { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 11px; align-items: start; }.meal-icon { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 12px; color: var(--qh-green-dark); background: var(--qh-sage-soft); font-weight: 800; }.meal-title > div { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }.meal-title span { color: var(--qh-muted); font-size: 11px; }.meal-title b { padding: 3px 6px; border-radius: 6px; color: var(--qh-orange-dark); background: var(--qh-orange-soft); font-size: 9px; }.meal-title p { margin: 6px 0 0; overflow: hidden; color: var(--qh-muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.meal-kcal { color: var(--qh-green-dark); font-size: 15px; white-space: nowrap; }.meal-kcal small { font-size: 9px; }
details { margin-top: 13px; border-top: 1px solid var(--qh-border); }summary { padding-top: 11px; color: var(--qh-muted); font-size: 11px; cursor: pointer; }.component-list { margin-top: 7px; }.component-list > div { display: grid; grid-template-columns: 1fr auto; gap: 3px 8px; padding: 8px 0; border-bottom: 1px dashed var(--qh-border); }.component-list span { display: grid; gap: 2px; }.component-list small, .component-list em { color: var(--qh-muted); font-size: 9px; font-style: normal; }.component-list .portion-detail { color: var(--qh-green-dark); line-height: 1.4; }.component-list em { grid-column: 1 / -1; }.component-list b { font-size: 10px; }.meal-card footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }.meal-card footer button, .row-actions button { border: 0; color: var(--qh-green-dark); background: transparent; font-size: 11px; cursor: pointer; }.danger { color: #a24a3f !important; }
.empty-state { display: grid; place-items: center; padding: 48px 20px; text-align: center; }.empty-state > div { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 16px; color: var(--qh-green-dark); background: var(--qh-sage-soft); font-weight: 800; }.empty-state strong { margin-top: 12px; }.empty-state p, .small-empty { color: var(--qh-muted); font-size: 12px; }.empty-state button { margin-top: 10px; padding: 9px 14px; border: 0; border-radius: 10px; color: white; background: var(--qh-green); font-weight: 700; cursor: pointer; }
.exercise-list { padding: 4px 20px 12px; }.exercise-list article { display: grid; grid-template-columns: 1fr auto auto; gap: 15px; align-items: center; padding: 15px 0; border-bottom: 1px solid var(--qh-border); }.exercise-list article:last-child { border-bottom: 0; }.exercise-list article > div:first-child { display: grid; gap: 4px; }.exercise-list span, .exercise-list small { color: var(--qh-muted); font-size: 11px; }.exercise-list b { color: var(--qh-orange-dark); }.row-actions { display: flex; }.small-empty { margin: 0; padding: 22px; }
.weight-card, .advice-panel { padding: 21px; }.weight-input { position: relative; margin-top: 17px; }.weight-input input { width: 100%; height: 52px; padding: 0 52px 0 13px; border: 1px solid var(--qh-border-strong); border-radius: 13px; color: var(--qh-text); background: white; font-size: 22px; font-weight: 800; }.weight-input b { position: absolute; top: 17px; right: 14px; color: var(--qh-muted); }.weight-card > button { width: 100%; min-height: 41px; margin-top: 10px; border: 0; border-radius: 11px; color: white; background: var(--qh-green); font-weight: 800; cursor: pointer; }.weight-card > small { display: block; margin-top: 10px; color: var(--qh-muted); line-height: 1.5; }
.advice-card { display: grid; grid-template-columns: auto 1fr auto; gap: 11px; width: 100%; margin-top: 11px; padding: 13px; border: 1px solid var(--qh-border); border-radius: 14px; text-align: left; background: white; cursor: pointer; }.advice-card > span { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 9px; color: var(--qh-green-dark); background: var(--qh-sage-soft); font-size: 10px; font-weight: 900; }.advice-card > div { min-width: 0; }.advice-card p { display: -webkit-box; margin: 4px 0 0; overflow: hidden; color: var(--qh-muted); font-size: 11px; line-height: 1.4; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }.advice-card > b { color: var(--qh-muted); font-size: 20px; }.advice-empty { display: grid; place-items: center; padding-top: 22px; text-align: center; }.advice-empty > div { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 16px; color: var(--qh-green-dark); background: var(--qh-sage-soft); font-size: 21px; }.advice-empty strong { margin-top: 12px; }.advice-empty p { margin: 7px 0 13px; color: var(--qh-muted); font-size: 12px; line-height: 1.55; }.advice-empty button { width: 100%; min-height: 42px; border: 0; border-radius: 11px; color: white; background: var(--qh-green); font-weight: 800; cursor: pointer; }
@media (max-width: 1080px) { .content-grid { grid-template-columns: 1fr; }.side-column { grid-template-columns: 1fr 1fr; }.meal-list { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .today-page { padding: 20px 16px 96px; }.page-header { align-items: flex-start; flex-direction: column; }.header-actions { width: 100%; }.header-actions button { flex: 1; }.metrics-grid { grid-template-columns: 1fr; }.side-column { grid-template-columns: 1fr; }.exercise-list article { grid-template-columns: 1fr auto; }.row-actions { grid-column: 1 / -1; justify-content: flex-end; } }
</style>
