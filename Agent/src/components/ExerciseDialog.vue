<script setup lang="ts">
import { vDialog } from '@/utils/dialog'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api, type Exercise, type Intensity, type MetActivity } from '@/api/qingheng'
import { ApiError } from '@/api/client'
import { useQinghengStore } from '@/stores/qingheng'
import UiIcon from './UiIcon.vue'

const props = defineProps<{ exercise?: Exercise | null }>()
const emit = defineEmits<{ close: [] }>()
const store = useQinghengStore()
const activities = ref<MetActivity[]>([])
const activityId = ref(props.exercise?.activity_id || '')
const intensity = ref<Intensity>(props.exercise?.intensity || 'medium')
const duration = ref(props.exercise?.duration_minutes || 30)
const recordedTime = ref((props.exercise?.recorded_time || new Date().toTimeString().slice(0, 5)).slice(0, 5))
const manual = ref(props.exercise?.estimate_source === 'manual_adjusted')
const manualLow = ref(props.exercise?.kcal.low || 0)
const manualHigh = ref(props.exercise?.kcal.high || 0)
const localError = ref('')
const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const uncertain = ref(false)
const locked = computed(() => submitting.value || store.busy || uncertain.value)
let disposed = false
const selected = computed(() => activities.value.find(item => item.id === activityId.value) || null)
const validDuration = computed(() => Number.isInteger(duration.value) && duration.value >= 1 && duration.value <= 600)
const validRange = computed(() => Number.isInteger(manualLow.value) && Number.isInteger(manualHigh.value)
  && manualLow.value >= 0 && manualHigh.value >= manualLow.value && manualHigh.value <= 20000)
const preview = computed(() => {
  if (manual.value) return validRange.value ? { low: manualLow.value, high: manualHigh.value } : null
  if (!selected.value || !store.profile || !validDuration.value) return null
  const value = selected.value.mets[intensity.value] * 3.5 * store.profile.current_weight_kg * duration.value / 200
  return { low: Math.round(value * .9), high: Math.round(value * 1.1) }
})
const canSubmit = computed(() => selected.value && validDuration.value && (!manual.value || validRange.value)
  && /^([01]\d|2[0-3]):[0-5]\d$/.test(recordedTime.value) && !loading.value && !loadError.value)

async function loadActivities() {
  if (loading.value && activities.value.length) return
  loading.value = true
  loadError.value = ''
  try {
    const result = await api.getMetActivities()
    if (disposed) return
    activities.value = result
    if (!activityId.value && result.length) activityId.value = result[0]!.id
  } catch (error) {
    if (!disposed) loadError.value = error instanceof Error ? error.message : '运动项目加载失败'
  } finally { if (!disposed) loading.value = false }
}
onMounted(loadActivities)
onBeforeUnmount(() => { disposed = true })
function close() { if (!submitting.value) emit('close') }
async function checkRecords() {
  if (store.busy) return
  await store.reloadToday()
  close()
}
async function submit() {
  if (!canSubmit.value || locked.value) return
  localError.value = ''
  submitting.value = true
  const payload = {
    activity_id: activityId.value, intensity: intensity.value,
    duration_minutes: duration.value, recorded_time: recordedTime.value,
    manual_kcal: manual.value ? { low: manualLow.value, high: manualHigh.value } : null,
  }
  try {
    await store.mutate(() => props.exercise ? api.updateExercise(props.exercise.id, payload) : api.createExercise(payload))
    store.notifySuccess(props.exercise ? '运动修改已保存' : '运动记录已保存')
    emit('close')
  } catch (error) {
    uncertain.value = !props.exercise && error instanceof ApiError && (error.status === 0 || [500, 502, 504].includes(error.status))
    localError.value = uncertain.value ? '暂时无法确认是否已保存。请先查看今日活动，确认没有这条记录后再添加。'
      : error instanceof Error ? error.message : '保存失败，请重试'
  } finally { submitting.value = false }
}
</script>

<template>
  <div v-dialog="close" class="modal-backdrop" @mousedown.self="close">
    <section class="exercise-dialog" role="dialog" aria-modal="true" aria-labelledby="exercise-title">
      <header class="dialog-header"><div><p class="eyebrow">活动记录</p><h2 id="exercise-title">{{ exercise ? '调整这次运动' : '动一动，也记一笔' }}</h2><p class="header-copy">记下项目与时长，补全今天的活动。</p></div><button class="close-button" type="button" aria-label="关闭运动记录" :disabled="submitting" @click="close">×</button></header>
      <div class="dialog-content">
        <div v-if="loading" class="load-state" role="status">正在加载运动项目…</div>
        <div v-else-if="loadError || !activities.length" class="load-state" role="alert"><p>{{ loadError || '暂时没有可选运动项目。' }}</p><button class="secondary" type="button" @click="loadActivities">重新加载</button></div>
        <fieldset class="exercise-fields" :disabled="locked || loading || !!loadError || !activities.length">
          <legend class="sr-only">运动信息</legend>
          <label class="activity-field"><span>运动项目</span><select v-model="activityId" aria-label="运动项目"><option v-if="activityId && !selected" :value="activityId" disabled>原项目已不可用，请重新选择</option><option v-for="activity in activities" :key="activity.id" :value="activity.id">{{ activity.name }}</option></select></label>
          <fieldset class="intensity-field"><legend>运动强度</legend><div class="intensity-options"><label v-for="option in [['low', '较低'], ['medium', '中等'], ['high', '较高']] as const" :key="option[0]" :class="{ active: intensity === option[0] }"><input v-model="intensity" type="radio" name="exercise-intensity" :value="option[0]" /><span>{{ option[1] }}</span></label></div></fieldset>
          <div class="form-grid"><label><span>运动时长</span><span class="input-unit"><input v-model.number="duration" type="number" min="1" max="600" step="1" aria-label="运动时长" /><b>分钟</b></span></label><label><span>记录时间</span><input v-model="recordedTime" type="time" aria-label="记录时间" /></label></div>
          <p v-if="!validDuration" class="field-error" role="alert">请输入 1–600 分钟的整数时长。</p>
          <div class="estimate"><span class="flame-icon"><UiIcon name="flame" /></span><div><span class="estimate-label">{{ manual ? '采用修正热量' : '预计运动消耗' }}</span><p><strong>{{ preview ? preview.low === preview.high ? preview.low.toLocaleString('zh-CN') : `${preview.low.toLocaleString('zh-CN')}–${preview.high.toLocaleString('zh-CN')}` : '—' }}</strong><small v-if="preview">kcal</small></p></div><span class="estimate-badge">{{ manual ? '手动填写' : '公式估算' }}</span></div>
          <section class="correction"><label class="toggle"><input v-model="manual" type="checkbox" /><span><strong>使用设备或个人数据</strong><small>有自己的热量记录？填写修正区间。</small></span></label><div v-if="manual" class="manual-range"><label><span>热量下限 · kcal</span><input v-model.number="manualLow" type="number" min="0" max="20000" step="1" aria-label="运动热量下限" /></label><label><span>热量上限 · kcal</span><input v-model.number="manualHigh" type="number" min="0" max="20000" step="1" aria-label="运动热量上限" /></label><p>这里填写本次运动的总热量；保存后采用此区间。</p><p v-if="!validRange" class="field-error" role="alert">请填写 0–20000 的整数，上限不能小于下限。</p></div></section>
        </fieldset>
        <details class="qh-disclosure estimate-note"><summary>了解估算方式</summary><div><p>根据运动项目、强度、时长与档案体重估算消耗，热量以区间呈现。设备数据可通过修正区间填写。</p><p v-if="selected">估算来源：MET · {{ selected.source_version }}</p></div></details>
        <p v-if="localError" class="form-error" role="alert">{{ localError }}</p>
      </div>
      <footer><span class="footer-note" role="status">{{ submitting ? '正在保存活动…' : uncertain ? '请先核对记录' : '保存后更新今日消耗' }}</span><div><button class="secondary" type="button" :disabled="submitting" @click="close">取消</button><button v-if="uncertain" class="primary" type="button" :disabled="store.busy" @click="checkRecords">查看今日活动</button><button v-else class="primary" type="button" :disabled="locked || !canSubmit" @click="submit">{{ submitting ? '保存中…' : exercise ? '保存修改' : '保存运动' }}</button></div></footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: var(--qh-overlay); backdrop-filter: blur(4px); }
.exercise-dialog { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; width: min(570px, 100%); max-height: calc(100vh - 40px); max-height: calc(100dvh - 40px); overflow: hidden; border: var(--qh-stroke) solid var(--qh-berry); border-radius: 24px; background: var(--qh-cream); box-shadow: var(--qh-shadow); }
.dialog-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 22px 24px; border-bottom: 1px solid var(--qh-border); background: var(--qh-oat); }
h2, p { margin: 0; } .eyebrow { color: var(--qh-muted); font-size: 12px; } h2 { margin-top: 5px; font-size: 26px; letter-spacing: -.03em; }
.header-copy { margin-top: 7px; color: var(--qh-muted); font-size: 13px; line-height: 1.7; }
.close-button { flex: 0 0 40px; width: 40px; height: 40px; border: 0; border-radius: 50%; color: var(--qh-muted); background: var(--qh-cream); font-size: 25px; cursor: pointer; }
.dialog-content { min-height: 0; overflow: auto; overscroll-behavior: contain; padding: 22px 24px; scroll-padding-block: 20px; }
.exercise-fields, .intensity-field { min-width: 0; margin: 0; padding: 0; border: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
label { display: grid; min-width: 0; gap: 7px; color: var(--qh-muted); font-size: 12px; }
input:not([type="checkbox"]):not([type="radio"]), select { width: 100%; min-width: 0; min-height: 46px; padding: 10px 12px; border: 1px solid var(--qh-border); border-radius: 12px; color: var(--qh-berry); background: var(--qh-cream); font-size: 16px; }
.intensity-field { margin-top: 18px; }.intensity-field legend { margin-bottom: 8px; color: var(--qh-muted); font-size: 12px; }
.intensity-options { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.intensity-options label { position: relative; display: grid; place-items: center; min-height: 44px; border: 1px solid var(--qh-border); border-radius: 12px; font-size: 14px; cursor: pointer; }
.intensity-options input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.intensity-options label.active { border-color: var(--qh-berry); background: var(--qh-oat); color: var(--qh-berry); font-weight: 600; }
.intensity-options label:focus-within { outline: 2px solid var(--qh-berry); outline-offset: 2px; }
.form-grid, .manual-range { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.input-unit { position: relative; display: block; }.input-unit input:not([type="checkbox"]):not([type="radio"]) { padding-right: 56px; }.input-unit b { position: absolute; top: 50%; right: 14px; transform: translateY(-50%); font-weight: 500; pointer-events: none; }
.estimate { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 20px; padding: 18px; border: 1px solid var(--qh-border); border-radius: 18px; background: var(--qh-oat); }
.flame-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 50%; background: color-mix(in srgb, var(--qh-yellow) 60%, var(--qh-cream)); color: var(--qh-red); }
.flame-icon .ui-icon { width: 25px; height: 25px; }.estimate-label { color: var(--qh-muted); font-size: 12px; }.estimate p { display: flex; align-items: baseline; flex-wrap: wrap; gap: 6px; margin-top: 3px; }.estimate strong { font-size: 29px; font-family: var(--qh-numeral); letter-spacing: -.035em; }.estimate small { font-size: 12px; }
.estimate-badge { margin-left: auto; padding: 5px 8px; background: var(--qh-cream); border-radius: var(--qh-radius-pill); color: var(--qh-muted); font-size: 11px; }
.correction { margin-top: 18px; padding: 14px; border: 1px solid var(--qh-border); border-radius: 16px; }.toggle { display: flex; align-items: start; gap: 10px; cursor: pointer; }.toggle input { width: 18px; height: 18px; flex-shrink: 0; margin: 3px 0 0; accent-color: var(--qh-berry); }.toggle > span { display: grid; gap: 4px; }.toggle strong { font-weight: 600; font-size: 13px; color: var(--qh-berry); }.toggle small { font-size: 12px; }
.manual-range p { grid-column: 1 / -1; font-size: 12px; color: var(--qh-muted); line-height: 1.7; }
.estimate-note { margin-top: 16px; }.estimate-note summary { font-size: 13px; }.estimate-note > div { padding: 14px 18px; }.estimate-note p { color: var(--qh-muted); font-size: 12px; line-height: 1.8; }.estimate-note p + p { margin-top: 6px; }
.field-error { margin-top: 10px; color: var(--qh-berry); font-size: 12px; line-height: 1.7; }.form-error, .load-state { padding: 12px; border: 1px solid var(--qh-border); border-radius: 12px; background: var(--qh-oat); font-size: 13px; line-height: 1.8; }.form-error { margin-top: 16px; }.load-state { margin-bottom: 16px; }.load-state button { margin-top: 10px; }
footer { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--qh-border); background: var(--qh-oat); }.footer-note { color: var(--qh-muted); font-size: 12px; } footer > div { display: flex; gap: 10px; }
.primary, .secondary { min-height: 44px; padding: 10px 18px; border-radius: var(--qh-radius-pill); font-size: 14px; cursor: pointer; }.primary { border: 1px solid var(--qh-berry); background: var(--qh-berry); color: var(--qh-cream); font-weight: 600; }.secondary { border: 1px solid var(--qh-border); background: var(--qh-cream); }
button:disabled { opacity: .5; cursor: default; }.exercise-fields:disabled { opacity: .6; }
@media (max-width: 760px) { .modal-backdrop { align-items: end; padding: 0; }.exercise-dialog { width: 100%; max-height: 94vh; max-height: 94dvh; border-radius: 22px 22px 0 0; }.dialog-header, .dialog-content { padding: 16px; }.close-button { width: 44px; height: 44px; flex-basis: 44px; } h2 { font-size: 22px; } footer { padding: 12px 16px calc(12px + env(safe-area-inset-bottom)); }.estimate { padding: 14px; }.estimate strong { font-size: 26px; } }
@media (max-width: 420px) { footer > div { width: 100%; } footer .primary { flex: 1; }.estimate-badge { margin-left: 54px; } }
</style>
