<script setup lang="ts">
import { computed, ref } from 'vue'

import AdviceDrawer from '@/components/AdviceDrawer.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'
import MealDialog from '@/components/MealDialog.vue'
import PhotoMealDialog from '@/components/PhotoMealDialog.vue'
import RangeMetric from '@/components/RangeMetric.vue'
import {
  api,
  type AdviceCard,
  type Exercise,
  type FollowUpMessage,
  type Meal,
} from '@/api/qingheng'
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
const scalePosition = (value: number) => Math.min(98, Math.max(2, ((value + 600) / 1600) * 100))
const balanceStyles = computed(() => {
  const summary = detail.value?.summary
  if (!summary) return {}
  const midpoint = (summary.deficit.low + summary.deficit.high) / 2
  const targetStart = scalePosition(summary.target_deficit.low)
  const targetEnd = scalePosition(summary.target_deficit.high)
  return {
    '--balance-position': `${scalePosition(midpoint)}%`,
    '--target-start': `${targetStart}%`,
    '--target-width': `${Math.max(3, targetEnd - targetStart)}%`,
  }
})
const balanceNarrative = computed(() => {
  const summary = detail.value?.summary
  if (!summary) return ''
  if (summary.deficit.high < 0) return '今天处于能量盈余区间'
  if (
    summary.deficit.low <= summary.target_deficit.high &&
    summary.deficit.high >= summary.target_deficit.low
  )
    return '今天的区间触及目标'
  if (summary.deficit.high < summary.target_deficit.low) return '今天的缺口低于目标'
  return '今天的缺口高于目标'
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
      <div class="header-meta">
        <p class="eyebrow">{{ dateLabel }}</p>
        <span>今日饮食记录</span>
      </div>
      <button class="secondary-action" @click="mealDialog = true"><span>＋</span> 手动记录</button>
    </header>

    <section class="photo-hero">
      <div class="photo-intro">
        <p class="photo-kicker"><i /> 拍照估算 · 主功能</p>
        <h1>拍下这一餐，<br /><em>自动拆解并入账。</em></h1>
        <p class="photo-lead">
          上传一张整餐照片，轻衡会识别食物与份量，给出热量区间，并直接加入今天的饮食记录。
        </p>
        <ol class="photo-steps" aria-label="拍照估算步骤">
          <li>
            <b>1</b><span><strong>拍整餐</strong><small>食物尽量完整入镜</small></span>
          </li>
          <li>
            <b>2</b><span><strong>确认餐次</strong><small>早餐、午餐或晚餐</small></span>
          </li>
          <li>
            <b>3</b><span><strong>自动入账</strong><small>保留估算来源与区间</small></span>
          </li>
        </ol>
        <button class="manual-link" @click="mealDialog = true">
          不方便拍照？改用手动记录 <span>→</span>
        </button>
      </div>

      <button class="capture-card" aria-label="打开拍照估算" @click="photoDialog = true">
        <i class="viewfinder-corner viewfinder-corner--tl" /><i
          class="viewfinder-corner viewfinder-corner--tr"
        /><i class="viewfinder-corner viewfinder-corner--bl" /><i
          class="viewfinder-corner viewfinder-corner--br"
        />
        <span class="camera-glyph"><i /><b /></span>
        <strong>打开相机或选择照片</strong>
        <small>支持 JPEG、PNG、WebP · 最大 10 MiB</small>
        <span class="capture-cta">开始拍照估算 <b>↗</b></span>
        <span class="capture-privacy"><i /> 原图识别后立即释放</span>
      </button>
    </section>

    <section class="day-overview">
      <header class="overview-heading">
        <div>
          <p class="eyebrow">拍照记录后的结果</p>
          <h2>今日能量概览</h2>
        </div>
        <span>{{ detail.meals.length }} 餐已入账</span>
      </header>
      <div class="overview-layout">
        <section class="balance-board" :style="balanceStyles">
          <header class="balance-heading">
            <div>
              <p class="eyebrow">平衡刻度</p>
              <h3>{{ balanceNarrative }}</h3>
            </div>
            <span class="privacy-stamp"><i /> 本机计算</span>
          </header>
          <div class="balance-ruler" aria-label="今日能量平衡位置">
            <div class="ruler-track">
              <span class="target-zone" /><span class="balance-marker"><i /></span>
            </div>
            <div class="ruler-labels">
              <span>能量盈余</span><span>接近平衡</span><span>目标缺口</span><span>缺口偏高</span>
            </div>
          </div>
        </section>
        <div class="metrics-grid">
          <RangeMetric label="今日摄入" :value="detail.summary.intake" />
          <RangeMetric
            label="预计消耗"
            :value="detail.summary.total_expenditure"
            tone="orange"
            :hint="`运动 ${detail.summary.exercise_expenditure.low === detail.summary.exercise_expenditure.high ? detail.summary.exercise_expenditure.low : `${detail.summary.exercise_expenditure.low}–${detail.summary.exercise_expenditure.high}`}`"
          />
          <RangeMetric
            :label="deficitLabel"
            :value="detail.summary.deficit"
            :tone="detail.summary.deficit.high < 0 ? 'orange' : 'green'"
            :hint="`目标 ${detail.summary.target_deficit.low}–${detail.summary.target_deficit.high}`"
          />
        </div>
      </div>
    </section>

    <div v-if="detail.summary.risk_flags.length" class="risk-chip">
      <span>!</span>
      <p>当前档案存在需要留意的健康风险；生成今日建议可查看原因。计算仍可继续。</p>
    </div>

    <section class="content-grid">
      <div class="main-column">
        <section class="panel meals-panel">
          <header class="panel-header">
            <div>
              <p class="eyebrow">今日记录</p>
              <h2>饮食账目</h2>
            </div>
            <span>{{ detail.meals.length }} 餐已记</span>
          </header>
          <div v-if="detail.meals.length" class="meal-list">
            <article v-for="meal in detail.meals" :key="meal.id" class="meal-card">
              <div class="meal-card__top">
                <div class="meal-icon">{{ meal.entry_method === 'photo' ? '▣' : '餐' }}</div>
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
          </div>
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
              <h2>运动账目</h2>
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
          <p class="eyebrow">更新能量基线</p>
          <h2>今日体重</h2>
          <div class="weight-input">
            <input v-model.number="weight" type="number" min="30" max="300" step="0.1" /><b>kg</b>
          </div>
          <button :disabled="store.busy" @click="saveWeight">更新体重与基线</button>
          <small>历史记录只读，不绘制趋势图。</small>
        </section>

        <section class="panel advice-panel">
          <p class="eyebrow">下一步</p>
          <h2>今日建议</h2>
          <template v-if="adviceCards.length">
            <button
              v-for="card in adviceCards"
              :key="card.type"
              class="advice-card"
              @click="openAdvice(card)"
            >
              <span>{{
                card.type === 'status' ? '01' : card.type === 'next_meal' ? '02' : '03'
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
            <strong>数据不会自动发送给 AI</strong>
            <p>点击后仅分析今天，并使用服务端已计算的热量事实。</p>
            <button :disabled="store.busy" @click="generateAdvice">
              {{ store.busy ? '生成中…' : '生成今日建议' }}
            </button>
          </div>
        </section>
      </aside>
    </section>

    <MealDialog v-if="mealDialog" :meal="editingMeal" @close="closeMealDialog" />
    <PhotoMealDialog v-if="photoDialog" @close="photoDialog = false" />
    <ExerciseDialog
      v-if="exerciseDialog"
      :exercise="editingExercise"
      @close="closeExerciseDialog"
    />
    <AdviceDrawer
      v-if="selectedAdvice"
      :card="selectedAdvice"
      :messages="conversations[selectedAdvice.type] || []"
      @close="selectedAdvice = null"
      @update:messages="updateConversation"
    />
  </main>
</template>

<style scoped>
.today-page {
  width: min(1360px, 100%);
  margin: 0 auto;
  padding: 42px 40px 64px;
}
.eyebrow {
  margin: 0;
  color: var(--qh-green-dark);
  font-family: var(--qh-data);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 17px;
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
  font-size: 9px;
  letter-spacing: 0.08em;
}
.secondary-action {
  min-height: 39px;
  padding: 0 14px;
  border: 1px solid var(--qh-border-strong);
  border-radius: 13px 5px 13px 5px;
  background: rgb(251 253 249 / 82%);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}
.secondary-action span {
  margin-right: 3px;
  font-family: var(--qh-data);
}
.secondary-action:hover {
  border-color: var(--qh-green);
  background: white;
}

.photo-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  gap: clamp(28px, 5vw, 72px);
  align-items: stretch;
  overflow: hidden;
  padding: clamp(30px, 4.5vw, 58px);
  border: 1px solid #244c3b;
  border-radius: 38px 12px 38px 12px;
  color: white;
  background: var(--qh-green-ink);
  box-shadow: 0 24px 56px rgb(18 56 42 / 18%);
}
.photo-hero::before {
  position: absolute;
  top: -230px;
  left: 31%;
  width: 620px;
  height: 480px;
  border: 1px solid rgb(185 227 199 / 12%);
  border-radius: 50%;
  content: '';
  transform: rotate(-13deg);
}
.photo-hero::after {
  position: absolute;
  bottom: -220px;
  left: -100px;
  width: 500px;
  height: 360px;
  border: 1px solid rgb(185 227 199 / 9%);
  border-radius: 50%;
  content: '';
  transform: rotate(10deg);
}
.photo-intro {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
.photo-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: #a9cbb5;
  font-family: var(--qh-data);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
}
.photo-kicker i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--qh-orange);
  box-shadow: 0 0 0 4px rgb(233 139 74 / 10%);
}
.photo-intro h1 {
  margin: 15px 0 14px;
  font-size: clamp(43px, 5.2vw, 70px);
  line-height: 1.08;
  letter-spacing: -0.075em;
}
.photo-intro h1 em {
  color: var(--qh-mint);
  font-style: normal;
}
.photo-lead {
  max-width: 640px;
  margin: 0;
  color: #b7cdbf;
  font-size: 14px;
  line-height: 1.8;
}
.photo-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
}
.photo-steps li {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 9px;
  min-width: 0;
  align-items: start;
}
.photo-steps li > b {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border: 1px solid rgb(185 227 199 / 22%);
  border-radius: 50%;
  color: var(--qh-mint);
  font-family: var(--qh-data);
  font-size: 9px;
}
.photo-steps span {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.photo-steps strong {
  font-size: 11px;
}
.photo-steps small {
  color: #779a86;
  font-size: 9px;
  line-height: 1.4;
}
.manual-link {
  margin-top: 24px;
  padding: 0;
  border: 0;
  color: #94b5a1;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}
.manual-link span {
  display: inline-block;
  margin-left: 5px;
}
.manual-link:hover {
  color: white;
}
.capture-card {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  min-height: 390px;
  padding: 34px 28px 25px;
  border: 1px solid rgb(185 227 199 / 24%);
  border-radius: 29px 8px 29px 8px;
  color: white;
  background: linear-gradient(145deg, rgb(255 255 255 / 9%), rgb(255 255 255 / 3%));
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 2%);
  cursor: pointer;
}
.capture-card:hover {
  border-color: rgb(185 227 199 / 48%);
  background: linear-gradient(145deg, rgb(255 255 255 / 13%), rgb(255 255 255 / 5%));
  transform: translateY(-2px);
}
.viewfinder-corner {
  position: absolute;
  width: 31px;
  height: 31px;
  border-color: #91bca0;
}
.viewfinder-corner--tl {
  top: 18px;
  left: 18px;
  border-top: 2px solid;
  border-left: 2px solid;
}
.viewfinder-corner--tr {
  top: 18px;
  right: 18px;
  border-top: 2px solid;
  border-right: 2px solid;
}
.viewfinder-corner--bl {
  bottom: 18px;
  left: 18px;
  border-bottom: 2px solid;
  border-left: 2px solid;
}
.viewfinder-corner--br {
  right: 18px;
  bottom: 18px;
  border-right: 2px solid;
  border-bottom: 2px solid;
}
.camera-glyph {
  position: relative;
  display: grid;
  width: 86px;
  height: 86px;
  place-items: center;
  margin-bottom: 20px;
  border: 1px solid rgb(185 227 199 / 24%);
  border-radius: 50%;
  background: rgb(185 227 199 / 8%);
  box-shadow: 0 0 0 11px rgb(185 227 199 / 3%);
}
.camera-glyph::before {
  width: 39px;
  height: 29px;
  border: 2px solid var(--qh-mint);
  border-radius: 7px;
  content: '';
}
.camera-glyph::after {
  position: absolute;
  top: 25px;
  width: 17px;
  height: 7px;
  border: 2px solid var(--qh-mint);
  border-bottom: 0;
  border-radius: 4px 4px 0 0;
  content: '';
}
.camera-glyph i {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid var(--qh-mint);
  border-radius: 50%;
}
.camera-glyph b {
  position: absolute;
  top: 35px;
  right: 27px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--qh-orange);
}
.capture-card > strong {
  font-family: var(--qh-display);
  font-size: 23px;
}
.capture-card > small {
  margin-top: 8px;
  color: #88a998;
  font-size: 10px;
}
.capture-cta {
  min-width: 210px;
  margin-top: 24px;
  padding: 13px 18px;
  border-radius: 15px 5px 15px 5px;
  color: var(--qh-green-ink);
  background: var(--qh-mint);
  font-size: 12px;
  font-weight: 900;
}
.capture-cta b {
  margin-left: 10px;
  font-family: var(--qh-data);
}
.capture-privacy {
  position: absolute;
  bottom: 25px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #759783;
  font-size: 9px;
}
.capture-privacy i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--qh-mint);
}

.day-overview {
  margin-top: 23px;
}
.overview-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 13px;
}
.overview-heading h2 {
  margin: 4px 0 0;
  font-size: 25px;
  letter-spacing: -0.03em;
}
.overview-heading > span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 9px;
}
.overview-layout {
  display: grid;
  grid-template-columns: minmax(290px, 0.75fr) minmax(0, 1.75fr);
  gap: 12px;
}
.balance-board {
  position: relative;
  overflow: hidden;
  min-width: 0;
  padding: 20px;
  border: 1px solid #c9d7cd;
  border-radius: 22px 7px 22px 7px;
  background: #e4eee7;
  box-shadow: var(--qh-shadow-soft);
}
.balance-board::after {
  position: absolute;
  right: -80px;
  bottom: -90px;
  width: 230px;
  height: 160px;
  border: 1px solid rgb(45 106 79 / 9%);
  border-radius: 50%;
  content: '';
}
.balance-heading {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.balance-heading .eyebrow {
  color: var(--qh-green-dark);
}
.balance-heading h3 {
  margin: 7px 0 0;
  font-size: 20px;
  letter-spacing: -0.035em;
}
.privacy-stamp {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 9px;
  border: 1px solid rgb(45 106 79 / 15%);
  border-radius: 999px;
  color: var(--qh-muted);
  background: rgb(255 255 255 / 34%);
  font-size: 9px;
}
.privacy-stamp i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--qh-green);
  box-shadow: 0 0 0 3px rgb(45 106 79 / 8%);
}
.balance-ruler {
  position: relative;
  z-index: 1;
  margin: 46px 3px 6px;
}
.ruler-track {
  position: relative;
  height: 2px;
  background: linear-gradient(90deg, #e98b4a 0%, #799a88 34%, #b9e3c7 65%, #f0b17f 100%);
}
.ruler-track::before,
.ruler-track::after {
  position: absolute;
  top: -3px;
  width: 1px;
  height: 8px;
  background: rgb(24 76 55 / 28%);
  content: '';
}
.ruler-track::before {
  left: 33.333%;
}
.ruler-track::after {
  right: 33.333%;
}
.target-zone {
  position: absolute;
  top: -6px;
  left: var(--target-start);
  width: var(--target-width);
  min-width: 18px;
  height: 14px;
  border: 1px solid var(--qh-green);
  border-radius: 999px;
  background: rgb(45 106 79 / 10%);
}
.balance-marker {
  position: absolute;
  top: 50%;
  left: var(--balance-position);
  width: 23px;
  height: 23px;
  border: 5px solid #fbfdf9;
  border-radius: 50%;
  background: var(--qh-orange);
  box-shadow: 0 0 0 5px rgb(255 255 255 / 10%);
  transform: translate(-50%, -50%);
}
.balance-marker i {
  position: absolute;
  top: -20px;
  left: 50%;
  width: 1px;
  height: 13px;
  background: var(--qh-green-dark);
  transform: translateX(-50%);
}
.ruler-labels {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin-top: 14px;
  color: #688074;
  font-family: var(--qh-data);
  font-size: 8px;
  letter-spacing: 0.04em;
}
.ruler-labels span:nth-child(2),
.ruler-labels span:nth-child(3) {
  text-align: center;
}
.ruler-labels span:last-child {
  text-align: right;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.metrics-grid :deep(.metric) {
  border-color: var(--qh-border);
  background: #f9fcf8;
  box-shadow: var(--qh-shadow-soft);
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
  grid-template-columns: minmax(0, 1fr) 318px;
  gap: 18px;
  margin-top: 18px;
}
.main-column,
.side-column {
  display: grid;
  align-content: start;
  gap: 18px;
}
.panel {
  overflow: hidden;
  border: 1px solid var(--qh-border);
  border-radius: 24px 8px 24px 8px;
  background: var(--qh-card);
  box-shadow: var(--qh-shadow-soft);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 24px 18px;
  border-bottom: 1px solid var(--qh-border);
}
.panel-header h2,
.weight-card h2,
.advice-panel h2 {
  margin: 4px 0 0;
  font-size: 22px;
  letter-spacing: -0.025em;
}
.panel-header > span {
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 9px;
}
.text-action {
  border: 0;
  color: var(--qh-green-dark);
  background: transparent;
  font-weight: 800;
  cursor: pointer;
}
.text-action:hover {
  color: var(--qh-orange-dark);
}
.meal-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  padding: 14px;
}
.meal-card {
  min-width: 0;
  padding: 17px;
  border: 1px solid transparent;
  border-radius: 17px 5px 17px 5px;
  background: #f1f5f1;
}
.meal-card:hover {
  border-color: var(--qh-border-strong);
  background: #f8faf7;
}
.meal-card__top {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 13px;
  align-items: start;
}
.meal-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid #c5d8ca;
  border-radius: 50%;
  color: var(--qh-green-dark);
  background: #e5efe7;
  font-family: var(--qh-display);
  font-weight: 800;
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
  font-size: 9px;
}
.meal-title b {
  padding: 3px 6px;
  border-radius: 6px;
  color: var(--qh-orange-dark);
  background: var(--qh-orange-soft);
  font-size: 9px;
}
.meal-title p {
  margin: 6px 0 0;
  overflow: hidden;
  color: var(--qh-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meal-kcal {
  color: var(--qh-green-dark);
  font-family: var(--qh-data);
  font-size: 14px;
  white-space: nowrap;
}
.meal-kcal small {
  font-size: 8px;
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
.component-list small,
.component-list em {
  color: var(--qh-muted);
  font-size: 9px;
  font-style: normal;
}
.component-list .portion-detail {
  color: var(--qh-green-dark);
  line-height: 1.4;
}
.component-list em {
  grid-column: 1 / -1;
  font-family: var(--qh-data);
}
.component-list b {
  font-family: var(--qh-data);
  font-size: 10px;
}
.meal-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}
.meal-card footer button,
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
.empty-state p,
.small-empty {
  color: var(--qh-muted);
  font-size: 12px;
}
.empty-state button {
  margin-top: 10px;
  padding: 10px 15px;
  border: 0;
  border-radius: 13px 5px 13px 5px;
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
.exercise-list span,
.exercise-list small {
  color: var(--qh-muted);
  font-size: 11px;
}
.exercise-list b {
  color: var(--qh-orange-dark);
  font-family: var(--qh-data);
  font-size: 12px;
}
.row-actions {
  display: flex;
}
.small-empty {
  margin: 0;
  padding: 24px;
}
.weight-card,
.advice-panel {
  padding: 23px;
}
.weight-card {
  position: relative;
  background: linear-gradient(145deg, #f9fcf8, #edf4ee);
}
.weight-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 54px;
  height: 4px;
  background: var(--qh-mint);
  content: '';
}
.weight-input {
  position: relative;
  margin-top: 18px;
}
.weight-input input {
  width: 100%;
  height: 56px;
  padding: 0 52px 0 14px;
  border: 1px solid var(--qh-border-strong);
  border-radius: 17px 6px 17px 6px;
  color: var(--qh-text);
  background: white;
  font-family: var(--qh-data);
  font-size: 24px;
  font-weight: 800;
}
.weight-input b {
  position: absolute;
  top: 19px;
  right: 14px;
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 11px;
}
.weight-card > button {
  width: 100%;
  min-height: 43px;
  margin-top: 10px;
  border: 0;
  border-radius: 14px 5px 14px 5px;
  color: white;
  background: var(--qh-green-ink);
  font-weight: 800;
  cursor: pointer;
}
.weight-card > button:hover,
.advice-empty button:hover {
  background: var(--qh-green);
}
.weight-card > small {
  display: block;
  margin-top: 10px;
  color: var(--qh-muted);
  line-height: 1.5;
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
  font-size: 9px;
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
  place-items: center;
  padding-top: 23px;
  text-align: center;
}
.advice-empty > div {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border: 1px solid #c5d8ca;
  border-radius: 50%;
  color: var(--qh-green-dark);
  background: var(--qh-sage-soft);
  font-size: 20px;
}
.advice-empty strong {
  margin-top: 12px;
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
  border-radius: 14px 5px 14px 5px;
  color: white;
  background: var(--qh-green-ink);
  font-weight: 800;
  cursor: pointer;
}

@media (prefers-reduced-motion: no-preference) {
  .photo-hero {
    animation: settle-in 380ms ease both;
  }
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
  .photo-hero {
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 32px;
  }
  .overview-layout {
    grid-template-columns: 1fr;
  }
  .content-grid {
    grid-template-columns: 1fr;
  }
  .side-column {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 900px) {
  .photo-hero {
    grid-template-columns: 1fr;
  }
  .capture-card {
    min-height: 320px;
  }
}
@media (max-width: 760px) {
  .today-page {
    padding: 26px 18px 104px;
  }
  .page-header {
    align-items: center;
  }
  .photo-hero {
    padding: 27px 22px 22px;
    border-radius: 28px 8px 28px 8px;
  }
  .photo-intro h1 {
    font-size: 46px;
  }
  .balance-board {
    padding: 20px;
    border-radius: 22px 7px 22px 7px;
  }
  .privacy-stamp {
    display: none;
  }
  .ruler-labels {
    font-size: 7px;
  }
  .metrics-grid {
    grid-template-columns: 1fr;
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
}
@media (max-width: 520px) {
  .header-meta > span {
    display: none;
  }
  .secondary-action {
    min-height: 36px;
    padding: 0 11px;
  }
  .photo-intro h1 {
    font-size: 41px;
  }
  .photo-lead {
    font-size: 13px;
  }
  .photo-steps {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 23px;
  }
  .capture-card {
    min-height: 315px;
    padding-inline: 18px;
  }
  .capture-card > strong {
    font-size: 20px;
  }
  .capture-cta {
    min-width: 205px;
  }
  .overview-heading h2 {
    font-size: 22px;
  }
  .balance-heading h3 {
    font-size: 18px;
  }
  .ruler-labels span:nth-child(2) {
    display: none;
  }
  .ruler-labels {
    grid-template-columns: repeat(3, 1fr);
  }
  .ruler-labels span:nth-child(3) {
    text-align: center;
  }
  .meal-card__top {
    grid-template-columns: auto 1fr;
  }
  .meal-kcal {
    grid-column: 2;
  }
  .panel-header {
    padding: 20px;
  }
}
</style>
