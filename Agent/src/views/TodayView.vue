<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import UiIcon from '@/components/UiIcon.vue'
import AdviceDrawer from '@/components/AdviceDrawer.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'
import MealDialog from '@/components/MealDialog.vue'
import PhotoMealDialog from '@/components/PhotoMealDialog.vue'
import EnergyOverview from '@/components/EnergyOverview.vue'
import MealRecordCard from '@/components/MealRecordCard.vue'
import ExerciseRecordCard from '@/components/ExerciseRecordCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const emit = defineEmits<{ openRecords: [] }>()
import {
  api,
  type AdviceCard,
  type Exercise,
  type FollowUpMessage,
  type Meal,
} from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

const store = useQinghengStore()
const pendingDelete = ref<{ title: string; description: string; action: () => Promise<void> } | null>(null)
const mealDialog = ref(false)
const photoDialog = ref(false)
const exerciseDialog = ref(false)
const editingMeal = ref<Meal | null>(null)
const editingExercise = ref<Exercise | null>(null)
const weight = ref<number | string>(store.today?.weight?.weight_kg ?? store.profile?.current_weight_kg ?? '')
const savingWeight = ref(false)
const generatingAdvice = ref(false)
const validWeight = computed(() => typeof weight.value === 'number' && Number.isFinite(weight.value)
  && weight.value >= 30 && weight.value <= 300
  && Math.abs(weight.value * 10 - Math.round(weight.value * 10)) < 1e-6)
const selectedAdvice = ref<AdviceCard | null>(null)
const conversations = ref<Record<string, FollowUpMessage[]>>({})

const detail = computed(() => store.today)
const weightHelp = computed(() => {
  if (!validWeight.value) return '请输入 30–300 kg 的体重，最多保留一位小数。'
  if (!detail.value?.weight) return weight.value === store.profile?.current_weight_kg
    ? '已带入档案体重，保存后计入今日。'
    : '保存后计入今日体重记录。'
  return '每天一次，记录身体的小变化。'
})
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
const adviceCards = computed(() => store.cachedAdvice?.cards || [])
const dateLabel = computed(() => {
  const value = detail.value?.summary.record_date
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  return `${date.getMonth() + 1}月${date.getDate()}日 · ${['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]}`
})

function editMeal(meal: Meal) {
  editingMeal.value = meal
  mealDialog.value = true
}

function editExercise(exercise: Exercise) {
  if (store.busy || !exercise.editable) return
  editingExercise.value = exercise
  exerciseDialog.value = true
}

function removeMeal(meal: Meal) {
  if (store.busy || !meal.deletable) return
  pendingDelete.value = {
    title: `删除${meal.display_name}？`,
    description: `将删除 ${meal.recorded_time.slice(0, 5)} 的这餐及食物明细，并更新今日能量概览。删除后无法恢复。`,
    action: async () => {
      if (store.busy) throw new Error('正在处理其他操作，请稍后重试。')
      await store.mutate(() => api.deleteMeal(meal.id))
      store.notifySuccess('餐食记录已删除')
    },
  }
}

function removeExercise(exercise: Exercise) {
  if (store.busy || !exercise.deletable) return
  pendingDelete.value = {
    title: `删除${exercise.activity_name}记录？`,
    description: `将删除 ${exercise.recorded_time.slice(0, 5)} 的 ${exercise.duration_minutes} 分钟活动，并更新今日消耗。删除后无法恢复。`,
    action: async () => {
      if (store.busy) throw new Error('正在处理其他操作，请稍后重试。')
      await store.mutate(() => api.deleteExercise(exercise.id))
      store.notifySuccess('活动记录已删除')
    },
  }
}

async function saveWeight() {
  if (store.busy || savingWeight.value || !validWeight.value || typeof weight.value !== 'number' || detail.value?.weight?.editable === false) return
  savingWeight.value = true
  try {
    await store.saveWeight(weight.value)
    store.notifySuccess('今日体重已保存')
  } catch {
    // The store displays the save/refresh error in the shared error toast.
  } finally {
    savingWeight.value = false
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
  if (store.busy || generatingAdvice.value) return
  generatingAdvice.value = true
  try {
    await store.generateAdvice()
  } catch {
    // The store exposes the API error through the app's error notification.
    // A Vue event handler must consume the rejection after it has been reported.
  } finally {
    generatingAdvice.value = false
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
        <h1>今天，轻一点。</h1>
      </div>
      <button class="secondary-action" @click="mealDialog = true"><span>＋</span> 手动记录</button>
    </header>

    <section class="day-overview">
      <EnergyOverview :summary="detail.summary" :has-meals="detail.meals.length > 0" @capture="photoDialog = true" />
    </section>

    <p v-if="!detail.meals.length" class="first-meal-tip">让食物完整入镜，选择餐次后即可入账。也可以使用右上角的手动记录。</p>

    <div v-if="detail.summary.risk_flags.length" class="risk-chip">
      <span>!</span>
      <p>当前档案存在需要留意的健康风险；生成今日建议可查看原因。计算仍可继续。</p>
    </div>

    <section class="content-grid">
      <div class="main-column">
        <section class="panel meals-panel">
          <header class="panel-header meals-header">
            <div><h2><UiIcon name="meal" /> 今日餐食</h2><p>展开一餐，查看食物与份量</p></div>
            <div class="meals-header-actions">
              <span class="meal-count">{{ detail.meals.length }} 餐已记</span>
              <button v-if="detail.meals.length" class="meal-add" @click="photoDialog = true"><UiIcon name="camera" />记录一餐</button>
            </div>
          </header>
          <TransitionGroup v-if="detail.meals.length" name="meal" tag="div" class="meal-list">
            <MealRecordCard
              v-for="meal in detail.meals" :key="meal.id" :meal="meal" :busy="store.busy"
              :class="{ 'meal-card--new': newMealIds.has(meal.id) }"
              @edit="editMeal" @remove="removeMeal"
            />
          </TransitionGroup>
          <div v-else class="empty-state">
            <span class="empty-state-icon"><UiIcon name="meal" /></span>
            <div class="empty-state-copy"><strong>从今天的第一餐开始</strong><p>拍下整餐，或手动填写食物与份量。</p></div>
            <div class="empty-state-actions">
              <button @click="photoDialog = true"><UiIcon name="camera" />拍照记录第一餐</button>
              <button class="empty-state__manual" @click="mealDialog = true">手动记录</button>
            </div>
          </div>
        </section>

        <section class="panel activity-panel" aria-labelledby="activity-heading">
          <header class="panel-header activity-header">
            <div><h2 id="activity-heading"><span class="activity-heading-icon"><UiIcon name="activity" /></span>活动记录</h2><p>记录活动，了解今天的额外消耗</p></div>
            <div class="activity-header-actions">
              <span>{{ detail.exercises.length }} 项已记</span>
              <button v-if="detail.exercises.length" class="activity-add" @click="exerciseDialog = true"><span aria-hidden="true">＋</span>记录运动</button>
            </div>
          </header>
          <div v-if="detail.exercises.length" class="exercise-list">
            <ExerciseRecordCard v-for="exercise in detail.exercises" :key="exercise.id" :exercise="exercise" :busy="store.busy" @edit="editExercise" @remove="removeExercise" />
          </div>
          <div v-else class="empty-state activity-empty">
            <span class="empty-state-icon"><UiIcon name="activity" /></span>
            <div class="empty-state-copy"><strong>今天还没有活动记录</strong><p>散步、骑行或拉伸，都可以记在这里。</p></div>
            <div class="empty-state-actions"><button @click="exerciseDialog = true"><span aria-hidden="true">＋</span>记录一次活动</button></div>
          </div>
          <details class="activity-explanation">
            <summary>日常消耗说明</summary>
            <p>日常基线按静息消耗 × 1.2 估算，已计入预计消耗。这里记录的运动消耗会另外计入。</p>
          </details>
        </section>
      </div>

      <aside class="side-column" aria-label="今日体重与建议">
        <section class="panel weight-card" aria-labelledby="weight-heading">
          <header class="side-card-header">
            <h2 id="weight-heading"><span class="side-card-icon side-card-icon--weight"><UiIcon name="scale" /></span>今日体重</h2>
            <span class="side-card-status" :class="{ 'side-card-status--saved': detail.weight && weight === detail.weight.weight_kg }">
              {{ detail.weight ? (weight === detail.weight.weight_kg ? '已记录' : '待保存') : '未记录' }}
            </span>
          </header>
          <form class="weight-form" @submit.prevent="saveWeight">
            <label for="today-weight">体重</label>
            <div class="weight-controls">
              <div class="weight-input">
                <input id="today-weight" v-model.number="weight" type="number" inputmode="decimal" min="30" max="300" step="0.1" required
                  :disabled="savingWeight || detail.weight?.editable === false" aria-label="今日体重（千克）" aria-describedby="weight-help" />
                <span aria-hidden="true">kg</span>
              </div>
              <button type="submit" :disabled="store.busy || !validWeight || detail.weight?.editable === false" aria-label="保存今日体重">
                {{ savingWeight ? '保存中…' : detail.weight ? '更新记录' : '保存体重' }}
              </button>
            </div>
            <p id="weight-help" class="side-card-note">{{ weightHelp }}</p>
          </form>
        </section>

        <section class="panel advice-panel" aria-labelledby="advice-heading" :aria-busy="generatingAdvice">
          <header class="side-card-header">
            <h2 id="advice-heading"><span class="side-card-icon side-card-icon--advice"><UiIcon name="leaf" /></span>今日建议</h2>
            <span class="side-card-status">{{ adviceCards.length ? adviceCards.length + ' 条建议' : '待生成' }}</span>
          </header>
          <div v-if="adviceCards.length" class="advice-list">
            <details v-for="card in adviceCards" :key="card.type" class="qh-disclosure advice-card" :class="'advice-card--' + card.type">
              <summary>
                <span class="advice-kind-icon"><UiIcon :name="card.type === 'status' ? 'chart' : card.type === 'next_meal' ? 'meal' : 'leaf'" /></span>
                <span class="advice-title"><small>{{ card.type === 'status' ? '今日状态' : card.type === 'next_meal' ? '下一餐' : '贴心提醒' }}</small><strong>{{ card.title }}</strong></span>
              </summary>
              <div class="advice-content">
                <p>{{ card.body }}</p>
                <ul v-if="card.bullets.length"><li v-for="(bullet, index) in card.bullets" :key="index">{{ bullet }}</li></ul>
                <footer><button type="button" :aria-label="'继续追问：' + card.title" @click="openAdvice(card)">继续追问 <span aria-hidden="true">→</span></button></footer>
              </div>
            </details>
            <p class="side-card-note">根据今日已记录的饮食和活动生成。</p>
          </div>
          <div v-else class="advice-empty">
            <strong>给下一餐一点参考</strong>
            <p>根据今天的饮食和活动，整理适合你的建议。</p>
            <button :disabled="store.busy" @click="generateAdvice">{{ generatingAdvice ? '生成中…' : '生成今日建议' }}</button>
            <p v-if="generatingAdvice" class="side-card-note" role="status">正在整理今日记录，请稍候…</p>
            <small v-else class="side-card-note">点击后会将今日必要记录发送给 AI 分析。</small>
          </div>
        </section>
      </aside>
    </section>
    <footer class="page-footer"><strong>轻衡 <span>QINGHENG</span></strong><span>记录真实的饮食 · 保持生活的平衡</span><em>轻一点，与生活更好一点。</em></footer>
  </main>
  <main v-else class="today-page today-loading" role="status">
    <span class="loading-symbol"><UiIcon name="record" /></span>
    <h2>{{ store.busy ? '正在更新今日记录…' : '今日记录暂未加载' }}</h2>
    <p>{{ store.busy ? '正在整理餐食、活动与能量摘要，请稍候。' : '请检查连接后重新加载，已保存的记录不会因此丢失。' }}</p>
    <button v-if="!store.busy" class="secondary-action" @click="store.reloadToday()">刷新今日数据</button>
  </main>

  <Transition name="dialog">
  <MealDialog v-if="mealDialog" :meal="editingMeal" @close="closeMealDialog" />
  </Transition>
  <ConfirmDialog v-if="pendingDelete" v-bind="pendingDelete" confirm-label="确认删除" @close="pendingDelete = null" @done="pendingDelete = null" />
  <Transition name="dialog">
  <PhotoMealDialog v-if="photoDialog" @close="photoDialog = false" @manual="photoDialog = false; editingMeal = null; mealDialog = true" />
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
.today-loading { display: grid; justify-items: center; align-content: center; gap: 14px; min-height: 55vh; text-align: center; }
.today-loading h2, .today-loading p { margin: 0; } .today-loading p { color: var(--qh-muted); font-size: 13px; line-height: 1.8; } .loading-symbol { display: grid; place-items: center; width: 54px; height: 54px; border-radius: 50%; background: var(--qh-oat); }

.today-page {
  width: min(1360px, 100%);
  margin: 0 auto;
  padding: 24px 28px 40px;

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

}
.header-meta { display: grid; gap: 8px; }
.page-header h1 { margin: 0; font-size: clamp(28px, 3vw, 40px); letter-spacing: -.03em; }
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
  border: var(--qh-stroke) solid var(--qh-border-strong);
  background: var(--qh-card);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  border-radius: var(--qh-radius-pill);
  border-color: var(--qh-brand);
}
.secondary-action span {
  margin-right: 3px;
  font-family: var(--qh-data);
}
.secondary-action:hover {
  border-color: var(--qh-brand);
  background: var(--qh-surface-subtle);
}

.day-overview {
  margin-top: 18px;
}

.risk-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 11px 14px;
  border: 1px solid var(--qh-yellow);
  border-radius: var(--qh-radius-control);
  color: var(--qh-text);
  background: var(--qh-orange-soft);
  font-size: 13px;
}
.risk-chip span {
  display: grid;
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  color: var(--qh-on-brand);
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
  border: var(--qh-stroke) solid var(--qh-border-strong);
  box-shadow: var(--qh-shadow-soft);
  border-radius: var(--qh-radius-card);
  background: var(--qh-card);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--qh-border);
  padding: 18px 20px 12px;
  background: var(--qh-surface-subtle);
}
.panel-header h2 {
  margin: 4px 0 0;
  font-size: 22px;
  letter-spacing: -0.025em;
}
.panel-header > span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 12px;
}
.meals-header { flex-wrap: wrap; align-items: center; gap: 12px; padding: 18px 20px; background: var(--qh-card); }
.meals-header h2 { display: flex; align-items: center; gap: 8px; margin: 0; }
.meals-header p { margin: 6px 0 0; font-size: 12px; color: var(--qh-muted); }
.meals-header-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 8px 12px; margin-left: auto; }
.meal-count { font-size: 12px; color: var(--qh-muted); white-space: nowrap; }
.meal-add { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 40px; padding: 8px 12px; border: 1px solid var(--qh-border-strong); border-radius: var(--qh-radius-pill); color: var(--qh-brand); background: var(--qh-card); font-size: 12px; white-space: nowrap; cursor: pointer; }
.meal-add .ui-icon { width: 18px; height: 18px; }
.meal-add:hover { background: var(--qh-oat); }
.meal-list { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; padding: 16px; }
.meal-list > :deep(.qh-disclosure) { margin: 0; }
.empty-state { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 16px; padding: 28px 24px; }
.empty-state-icon { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 50%; color: var(--qh-berry); background: var(--qh-mint); }
.empty-state-copy strong { font-size: 17px; }
.empty-state-copy p { margin: 6px 0 0; color: var(--qh-muted); font-size: 13px; line-height: 1.6; }
.empty-state-actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.empty-state button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 10px 16px; border: 1px solid var(--qh-brand); border-radius: var(--qh-radius-pill); color: var(--qh-on-brand); background: var(--qh-brand); font-size: 13px; font-weight: 600; cursor: pointer; }
.empty-state button .ui-icon { width: 20px; height: 20px; }
.empty-state button:not(.empty-state__manual):hover { background: var(--qh-brand-hover); }
.empty-state .empty-state__manual { color: var(--qh-brand); background: transparent; border-color: var(--qh-border); }
.empty-state .empty-state__manual:hover { background: var(--qh-oat); }
.activity-header { flex-wrap: wrap; align-items: center; gap: 12px; padding: 18px 20px; }
.activity-header h2 { display: flex; align-items: center; gap: 9px; margin: 0; }
.activity-header p { margin: 6px 0 0; color: var(--qh-muted); font-size: 12px; }
.activity-heading-icon { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--qh-berry); color: white; }
.activity-heading-icon .ui-icon { width: 20px; height: 20px; }
.activity-header-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px 12px; margin-left: auto; }
.activity-header-actions > span { color: var(--qh-muted); font-size: 12px; white-space: nowrap; }
.activity-add { display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 8px 12px; border: 1px solid var(--qh-border-strong); border-radius: var(--qh-radius-pill); color: var(--qh-brand); background: var(--qh-card); font-size: 12px; white-space: nowrap; cursor: pointer; }
.activity-add:hover { background: var(--qh-cream); }
.exercise-list { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; padding: 16px; }
.exercise-list > :deep(.qh-disclosure) { margin: 0; }
.activity-empty .empty-state-icon { color: white; background: var(--qh-berry); }
.activity-explanation { margin: 0 18px 16px; padding-top: 10px; border-top: 1px solid var(--qh-border); color: var(--qh-muted); font-size: 12px; }
.activity-explanation summary { cursor: pointer; padding: 5px 0; width: fit-content; }
.activity-explanation p { margin: 6px 0 0; line-height: 1.7; }
.side-column { min-width: 0; }
.side-card-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 16px 18px; border-bottom: 1px solid var(--qh-border); background: var(--qh-oat); }
.side-card-header h2 { display: flex; align-items: center; gap: 9px; margin: 0; font-size: 20px; letter-spacing: -.025em; }
.side-card-icon { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; color: var(--qh-berry); }
.side-card-icon .ui-icon { width: 20px; height: 20px; }
.side-card-icon--weight { background: var(--qh-blue); }
.side-card-icon--advice { background: var(--qh-mint); }
.side-card-status { flex-shrink: 0; padding: 3px 8px; border-radius: var(--qh-radius-pill); color: var(--qh-muted); font-size: 12px; }
.side-card-status--saved { color: var(--qh-green-ink); background: var(--qh-mint); }
.weight-form { padding: 18px; }
.weight-form > label { display: block; margin-bottom: 8px; color: var(--qh-muted); font-size: 12px; }
.weight-controls { display: flex; flex-wrap: wrap; align-items: stretch; gap: 10px; }
.weight-input { position: relative; flex: 1 1 130px; min-width: 0; }
.weight-input input { width: 100%; height: 54px; padding: 0 48px 0 14px; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-control); color: var(--qh-text); background: var(--qh-card); font-family: var(--qh-numeral); font-size: 28px; font-weight: 700; }
.weight-input > span { position: absolute; right: 16px; top: 50%; transform: translateY(-50%); pointer-events: none; color: var(--qh-muted); font-size: 13px; }
.weight-input input { appearance: textfield; }
.weight-input input::-webkit-inner-spin-button, .weight-input input::-webkit-outer-spin-button { appearance: none; margin: 0; }
.weight-controls > button { min-height: 48px; padding: 10px 18px; border: 1px solid var(--qh-brand); border-radius: var(--qh-radius-pill); color: var(--qh-on-brand); background: var(--qh-brand); font-size: 14px; font-weight: 600; white-space: nowrap; cursor: pointer; }
.weight-controls > button:not(:disabled):hover, .advice-empty > button:not(:disabled):hover { background: var(--qh-brand-hover); }
.weight-controls > button:disabled, .advice-empty > button:disabled { opacity: .55; cursor: not-allowed; }
.side-card-note { display: block; margin: 10px 0 0; font-size: 12px; line-height: 1.65; color: var(--qh-muted); }
.advice-list { padding: 14px; }
.advice-card > summary { display: grid; grid-template-columns: 30px minmax(0, 1fr); align-items: center; gap: 10px; padding: 14px 40px 14px 14px; }
.advice-card > summary::before, .advice-card > summary::after { right: 16px; }
.advice-card > summary:focus-visible { outline-offset: -4px; }
.advice-card > summary:hover { background: color-mix(in srgb, var(--qh-oat) 94%, var(--qh-berry)); }
.advice-card[open] > summary { border-bottom: 1px solid var(--qh-border); }
.advice-kind-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: var(--qh-berry); background: var(--qh-blue); }
.advice-kind-icon .ui-icon { width: 18px; height: 18px; }
.advice-card--next_meal .advice-kind-icon { background: var(--qh-mint); }
.advice-card--risk_or_encouragement .advice-kind-icon { background: var(--qh-yellow); }
.advice-title { display: grid; gap: 3px; min-width: 0; }
.advice-title small { color: var(--qh-muted); font-size: 11px; font-weight: 400; }
.advice-title strong { font-size: 15px; font-weight: 600; line-height: 1.5; overflow-wrap: anywhere; }
.advice-content { padding: 14px 16px; font-size: 13px; line-height: 1.75; color: var(--qh-muted); overflow-wrap: anywhere; }
.advice-content p { margin: 0; white-space: pre-line; }
.advice-content ul { margin: 10px 0 0; padding-left: 18px; }
.advice-content li + li { margin-top: 6px; }
.advice-content li::marker { color: var(--qh-berry); }
.advice-content footer { display: flex; justify-content: flex-end; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--qh-border); }
.advice-content button { display: inline-flex; align-items: center; gap: 12px; min-height: 36px; padding: 6px 12px; border: 1px solid var(--qh-border-strong); border-radius: var(--qh-radius-pill); background: var(--qh-card); color: var(--qh-brand); font-size: 12px; cursor: pointer; }
.advice-content button:hover { background: var(--qh-oat); }
.advice-empty { padding: 20px 18px; }
.advice-empty > strong { font-size: 16px; }
.advice-empty > p:not(.side-card-note) { margin: 8px 0 16px; color: var(--qh-muted); font-size: 13px; line-height: 1.7; }
.advice-empty > button { width: 100%; min-height: 44px; padding: 10px 16px; border: 1px solid var(--qh-brand); border-radius: var(--qh-radius-pill); color: var(--qh-on-brand); background: var(--qh-brand); font-size: 14px; font-weight: 600; cursor: pointer; }
.first-meal-tip {
  margin: 10px 4px 0;
  font-size: 12px;
  color: var(--qh-muted);
  line-height: 1.7;
}
.header-meta .eyebrow {
  font-size: 16px;
  letter-spacing: 0;
}
.date-menu { position: relative; margin: 0; border: 0; z-index: 5; }
.date-menu > summary { list-style: none; padding: 4px 0; cursor: pointer; }
.date-menu > summary::-webkit-details-marker { display: none; }
.date-menu > div { position: absolute; top: 100%; left: 0; width: 210px; padding: 14px; background: var(--qh-card); border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-control); box-shadow: var(--qh-shadow-soft); }
.date-menu p { margin: 0 0 12px; font-size: 12px; color: var(--qh-muted); }
.date-menu button { border: 0; background: var(--qh-brand-soft); padding: 10px 12px; border-radius: 8px; cursor: pointer; }
.page-footer { display: flex; align-items: center; flex-wrap: wrap; gap: 18px; padding: 26px 0 4px; margin-top: 20px; border-top: 1px solid var(--qh-border); font-size: 12px; color: var(--qh-muted); }
.page-footer strong { color: var(--qh-brand); font-family: var(--qh-display); }
.page-footer strong span { font: 10px var(--qh-body); letter-spacing: .14em; margin-left: 12px; }
.page-footer em { margin-left: auto; font: 15px var(--qh-display); }
@media (prefers-reduced-motion: no-preference) {
  .meal-card--new { animation: meal-added 400ms ease; }
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
}
@media (max-width: 1100px) {
  .content-grid {
    grid-template-columns: minmax(0, 1.2fr) minmax(280px, 1fr);
  }
  .side-column {
    grid-template-columns: 1fr;
  }
}
@media (min-width: 761px) and (max-width: 1050px) {
  .content-grid { grid-template-columns: minmax(0, 1fr); }
  .side-column { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .today-page {
    padding: 22px 12px calc(104px + env(safe-area-inset-bottom));
  }
  .side-column {
    grid-template-columns: 1fr;
  }
  .day-overview {
    margin-top: 20px;
  }
  .meal-list, .exercise-list { padding: 12px; }
  .content-grid {
    grid-template-columns: 1fr;
  }
  .secondary-action, .meal-add, .activity-add, .advice-content button { min-height: 44px; }
}
@media (max-width: 520px) {
  .page-header { align-items: flex-start; gap: 10px; }
  .page-header h1 { font-size: 26px; }
  .secondary-action { flex-shrink: 0; white-space: nowrap; }
  .header-meta > span {
    display: none;
  }
  .secondary-action {
    min-height: 44px;
    padding: 0 11px;
  }
  .empty-state { padding: 22px 16px; gap: 12px; }
  .panel-header {
    padding: 16px;
  }
  .side-card-header { padding: 14px 16px; }
  .side-card-header h2, .panel-header h2 { font-size: 20px; }
  .weight-form { padding: 16px; }
  .advice-list { padding: 12px; }
  .advice-content { font-size: 14px; }
  .page-footer { gap: 10px; padding-top: 20px; }
  .page-footer em { margin-left: 0; }
}
@media (max-width: 360px) {
  .page-header { flex-wrap: wrap; }
  .page-header .secondary-action { margin-left: auto; }
}

</style>
