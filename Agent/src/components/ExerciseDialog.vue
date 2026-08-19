<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, type Exercise, type Intensity, type MetActivity } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

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

const selected = computed(() => activities.value.find((item) => item.id === activityId.value) || null)
const preview = computed(() => {
  if (!selected.value || !store.profile) return null
  const met = selected.value.mets[intensity.value]
  const value = (met * 3.5 * store.profile.current_weight_kg * duration.value) / 200
  return { low: Math.round(value * 0.9), high: Math.round(value * 1.1) }
})

onMounted(async () => {
  try {
    activities.value = await api.getMetActivities()
    if (!activityId.value && activities.value.length) activityId.value = activities.value[0]!.id
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '运动模板加载失败'
  }
})

async function submit() {
  if (!activityId.value) return
  localError.value = ''
  if (manual.value && (manualLow.value < 0 || manualHigh.value < manualLow.value)) {
    localError.value = '请输入有效的修正区间'
    return
  }
  const payload = {
    activity_id: activityId.value,
    intensity: intensity.value,
    duration_minutes: duration.value,
    recorded_time: recordedTime.value,
    manual_kcal: manual.value ? { low: manualLow.value, high: manualHigh.value } : null,
  }
  try {
    await store.mutate(() =>
      props.exercise ? api.updateExercise(props.exercise.id, payload) : api.createExercise(payload),
    )
    emit('close')
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '保存失败'
  }
}
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="emit('close')">
    <section class="exercise-dialog" role="dialog" aria-modal="true">
      <header><div><p>运动消耗</p><h2>{{ exercise ? '编辑运动' : '记录运动' }}</h2></div><button @click="emit('close')">×</button></header>
      <div class="form-grid">
        <label><span>项目</span><select v-model="activityId"><option v-for="activity in activities" :key="activity.id" :value="activity.id">{{ activity.name }}</option></select></label>
        <label><span>强度</span><select v-model="intensity"><option value="low">较低</option><option value="medium">中等</option><option value="high">较高</option></select></label>
        <label><span>时长</span><div class="input-unit"><input v-model.number="duration" type="number" min="1" max="600" /><b>分钟</b></div></label>
        <label><span>时间</span><input v-model="recordedTime" type="time" /></label>
      </div>
      <div v-if="preview" class="estimate"><span>本地 MET 估算</span><strong>{{ preview.low }}–{{ preview.high }} kcal</strong><small>{{ selected?.source_version }}</small></div>
      <label class="toggle"><input v-model="manual" type="checkbox" /><span>使用设备或个人数据修正区间</span></label>
      <div v-if="manual" class="manual-range"><label><span>下限</span><input v-model.number="manualLow" type="number" min="0" /></label><span>—</span><label><span>上限</span><input v-model.number="manualHigh" type="number" min="0" /></label><b>kcal</b></div>
      <p v-if="localError" class="form-error">{{ localError }}</p>
      <footer><button class="secondary" @click="emit('close')">取消</button><button class="primary" :disabled="store.busy || !activityId" @click="submit">保存运动</button></footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(33 38 30 / 38%); backdrop-filter: blur(4px); }
.exercise-dialog { width: min(560px, 100%); padding: 26px; border: 1px solid var(--qh-border); border-radius: 24px; background: var(--qh-card); box-shadow: 0 28px 80px rgb(30 45 26 / 22%); }
header { display: flex; align-items: flex-start; justify-content: space-between; } header p, h2 { margin: 0; } header p { color: var(--qh-green-dark); font-size: 12px; font-weight: 800; } h2 { margin-top: 5px; font-size: 24px; } header button { width: 38px; height: 38px; border: 0; border-radius: 12px; color: var(--qh-muted); background: var(--qh-sage-soft); font-size: 25px; cursor: pointer; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 24px; } label { display: grid; gap: 7px; color: var(--qh-muted); font-size: 12px; font-weight: 700; } input, select { width: 100%; height: 43px; padding: 0 11px; border: 1px solid var(--qh-border-strong); border-radius: 11px; color: var(--qh-text); background: white; }.input-unit { position: relative; }.input-unit input { padding-right: 52px; }.input-unit b { position: absolute; top: 13px; right: 12px; }
.estimate { display: grid; grid-template-columns: 1fr auto; gap: 4px 15px; margin-top: 18px; padding: 16px; border-radius: 14px; background: var(--qh-sage-soft); }.estimate span { color: var(--qh-muted); }.estimate strong { color: var(--qh-green-dark); font-size: 20px; }.estimate small { grid-column: 1 / -1; color: var(--qh-muted); }
.toggle { display: flex; align-items: center; gap: 9px; margin-top: 18px; }.toggle input { width: 17px; height: 17px; accent-color: var(--qh-green); }
.manual-range { display: grid; grid-template-columns: 1fr auto 1fr auto; gap: 10px; align-items: end; margin-top: 12px; }.manual-range > span, .manual-range > b { padding-bottom: 13px; color: var(--qh-muted); }
.form-error { padding: 10px 12px; border-radius: 10px; color: #8f3f35; background: #fff0ed; font-size: 13px; }
footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px; } footer button { min-height: 43px; padding: 0 17px; border-radius: 12px; font-weight: 800; cursor: pointer; }.secondary { border: 1px solid var(--qh-border); background: white; }.primary { border: 0; color: white; background: var(--qh-green); }.primary:disabled { opacity: .5; }
@media (max-width: 560px) { .modal-backdrop { align-items: end; padding: 0; }.exercise-dialog { border-radius: 22px 22px 0 0; }.form-grid { grid-template-columns: 1fr; } }
</style>
