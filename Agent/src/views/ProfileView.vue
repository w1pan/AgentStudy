<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { type ProfilePayload } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'
import LeafMark from '@/components/LeafMark.vue'
import UiIcon from '@/components/UiIcon.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

withDefaults(defineProps<{ onboarding?: boolean }>(), { onboarding: false })
const emit = defineEmits<{ saved: [] }>()
const store = useQinghengStore()
const saving = ref(false)
const saved = ref(false)
const showClearConfirmation = ref(false)

const form = reactive<ProfilePayload>({
  age: 30,
  biological_sex: 'female',
  height_cm: 165,
  current_weight_kg: 60,
  deficit_preset: 'gentle',
})

watch(
  () => store.profile,
  (profile) => {
    if (!profile) return
    Object.assign(form, {
      age: profile.age,
      biological_sex: profile.biological_sex,
      height_cm: profile.height_cm,
      current_weight_kg: profile.current_weight_kg,
      deficit_preset: profile.deficit_preset,
    })
  },
  { immediate: true },
)

const presetCopy = computed(() =>
  form.deficit_preset === 'gentle'
    ? '250–350'
    : '500–600',
)
watch(form, () => { saved.value = false }, { flush: 'sync' })

async function save() {
  if (saving.value || store.busy) return
  saving.value = true
  saved.value = false
  try {
    await store.saveProfile({ ...form })
    saved.value = true
    store.notifySuccess('档案已保存')
    emit('saved')
  } catch {
    // Keep the entered values; the store displays the error in the shared toast.
  } finally {
    saving.value = false
  }
}

async function clearHistory() {
  if (store.busy || saving.value) throw new Error('正在保存其他内容，请稍后重试。')
  await store.clearHistory()
  store.notifySuccess('历史记录已清空，个人档案已保留')
}

</script>

<template>
  <main class="profile-page" :class="{ 'profile-page--onboarding': onboarding }">
    <header class="page-header">
      <div><p class="eyebrow">{{ onboarding ? '开始使用轻衡' : '了解自己，轻一点' }}</p><h1>{{ onboarding ? '先建立你的能量基线' : '我的档案' }}</h1><p class="page-intro">{{ onboarding ? '填写身体信息，开始记录每一天。' : '身体信息与目标，随着你的变化更新。' }}</p></div>
      <span class="brand-seal"><LeafMark /></span>
    </header>

    <div class="profile-layout">
      <form class="profile-form" @submit.prevent="save">
        <fieldset class="form-fields" :disabled="store.busy || saving">
          <legend class="sr-only">个人档案设置</legend>
          <section class="profile-card">
            <header class="card-header"><h2><span class="section-icon person-icon"><UiIcon name="person" /></span>身体信息</h2><span>用于能量估算</span></header>
            <div class="body-fields">
              <label for="profile-age"><span>年龄</span><span class="input-with-unit"><input id="profile-age" v-model.number="form.age" type="number" min="18" max="64" step="1" required aria-describedby="age-note" /><b>岁</b></span><small id="age-note">适用于 18–64 岁健康成人</small></label>
              <label for="profile-sex"><span>生理性别</span><select id="profile-sex" v-model="form.biological_sex" required aria-describedby="sex-note"><option value="female">女</option><option value="male">男</option></select><small id="sex-note">仅用于能量估算公式</small></label>
              <label for="profile-height"><span>身高</span><span class="input-with-unit"><input id="profile-height" v-model.number="form.height_cm" type="number" min="120" max="230" step="0.1" required /><b>cm</b></span></label>
              <label for="profile-weight"><span>当前体重</span><span class="input-with-unit"><input id="profile-weight" v-model.number="form.current_weight_kg" type="number" min="30" max="300" step="0.1" required /><b>kg</b></span></label>
            </div>
          </section>

          <section class="profile-card goal-card">
            <header class="card-header"><h2><span class="section-icon goal-icon"><UiIcon name="leaf" /></span>目标设置</h2><span>选择适合你的节奏</span></header>
            <div class="goal-body">
              <fieldset class="preset-field">
                <legend>减脂档位</legend>
                <label class="preset-option" :class="{ active: form.deficit_preset === 'gentle' }"><input v-model="form.deficit_preset" type="radio" name="deficit-preset" value="gentle" /><span class="preset-copy"><strong>温和</strong><span>较小的每日目标缺口</span><span class="preset-range"><b>250–350</b> kcal / 日</span></span></label>
                <label class="preset-option" :class="{ active: form.deficit_preset === 'standard' }"><input v-model="form.deficit_preset" type="radio" name="deficit-preset" value="standard" /><span class="preset-copy"><strong>标准</strong><span>较大的每日目标缺口</span><span class="preset-range"><b>500–600</b> kcal / 日</span></span></label>
              </fieldset>
              <p class="target-note">所选目标缺口 <strong>{{ presetCopy }} kcal / 日</strong>，保存后用于能量概览。</p>
            </div>
          </section>
        </fieldset>

        <details class="qh-disclosure formula-note">
          <summary>估算与信息使用说明</summary>
          <div class="disclosure-body"><p>通过 Mifflin–St Jeor 公式估算静息消耗，再结合日常活动与已记录运动，估算全天消耗。饮食热量以区间呈现。</p><p>档案保存在当前服务；使用 AI 功能时会向模型服务发送必要信息。</p><p>公式估算不能替代医疗、营养或运动专业意见。</p></div>
        </details>
        <div class="form-actions"><p class="save-feedback" role="status">{{ saving ? '正在保存档案…' : saved ? '档案已保存' : onboarding ? '完成后即可开始记录饮食与活动。' : '修改信息后，记得保存档案。' }}</p><button class="primary-button" type="submit" :disabled="store.busy || saving">{{ saving ? '保存中…' : onboarding ? '完成建档并进入今日' : '保存档案' }}</button></div>
      </form>

      <aside v-if="store.profile && !onboarding" class="profile-summary profile-card">
        <header class="card-header"><h2><span class="section-icon summary-icon"><UiIcon name="chart" /></span>已保存的估算</h2></header>
        <div class="summary-content">
          <p class="summary-intro">根据已保存档案计算；修改后保存即可更新。</p>
          <dl>
            <div class="summary-row"><dt><span class="metric-icon bmi-icon"><UiIcon name="scale" /></span>BMI</dt><dd><strong>{{ store.profile.bmi }}</strong></dd></div>
            <div class="summary-row"><dt><span class="metric-icon flame-icon"><UiIcon name="flame" /></span>静息消耗</dt><dd><strong>{{ store.profile.rmr_kcal.toLocaleString('zh-CN') }}</strong><small>kcal / 日</small></dd></div>
            <div class="summary-row"><dt><span class="metric-icon target-icon"><UiIcon name="leaf" /></span>目标缺口</dt><dd><strong>{{ store.profile.target_deficit.low }}–{{ store.profile.target_deficit.high }}</strong><small>kcal / 日</small></dd></div>
          </dl>
          <p class="summary-footnote">估算值是记录时的参考，实际需求会随身体与活动变化。</p>
        </div>
      </aside>
    </div>

    <details v-if="!onboarding" class="qh-disclosure data-management">
      <summary>历史记录管理</summary>
      <div class="data-management-body"><div><strong>清空历史记录</strong><p>将删除饮食、运动、每日体重和日汇总。清空后无法恢复，个人档案会保留。</p></div><button class="danger-link" type="button" :disabled="store.busy || saving" @click="showClearConfirmation = true">清空历史记录</button></div>
    </details>
  </main>
  <ConfirmDialog v-if="showClearConfirmation" title="清空全部历史记录？" description="所有饮食、运动、每日体重和日汇总都将被删除，无法恢复。个人档案会保留。" confirm-label="确认清空" confirmation-text="清空全部历史记录" :action="clearHistory" @close="showClearConfirmation = false" @done="showClearConfirmation = false" />
</template>

<style scoped>
.profile-page { width: min(1200px, 100%); margin: 0 auto; padding: 30px 28px 40px; }
.profile-page--onboarding { max-width: 850px; padding-top: 44px; padding-bottom: calc(32px + env(safe-area-inset-bottom)); }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 26px; }
.eyebrow { margin: 0; color: var(--qh-muted); font-size: 12px; font-weight: 600; letter-spacing: .08em; }
.page-header h1 { margin: 5px 0 8px; font-size: 36px; letter-spacing: -.04em; line-height: 1.35; }
.page-intro { margin: 0; color: var(--qh-muted); font-size: 14px; line-height: 1.7; }
.brand-seal { display: grid; flex: 0 0 60px; width: 60px; height: 60px; place-items: center; border-radius: 50%; color: var(--qh-cream); background: var(--qh-berry); }
.brand-seal .leaf-mark { width: 36px; height: 32px; }
.profile-layout { display: grid; grid-template-columns: minmax(0, 1fr) 290px; align-items: start; gap: 22px; }
.profile-page--onboarding .profile-layout { grid-template-columns: minmax(0, 1fr); }
.profile-form, .form-fields { display: grid; gap: 18px; min-width: 0; }
.form-fields { margin: 0; padding: 0; border: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0; }
.profile-card { min-width: 0; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-card); background: var(--qh-cream); }
.card-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; padding: 16px 20px; border-bottom: 1px solid var(--qh-border); border-radius: 20px 20px 0 0; background: var(--qh-oat); }
.card-header h2 { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 20px; }
.card-header > span { color: var(--qh-muted); font-size: 12px; }
.section-icon, .metric-icon { display: inline-grid; place-items: center; flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; }
.section-icon .ui-icon { width: 20px; height: 20px; }
.person-icon, .bmi-icon { background: var(--qh-blue); }
.goal-icon, .target-icon { background: var(--qh-mint); }
.summary-icon { background: var(--qh-yellow); }
.body-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; gap: 22px 18px; padding: 24px 20px; }
.body-fields label { display: grid; min-width: 0; gap: 8px; font-size: 14px; font-weight: 600; }
.body-fields label small { color: var(--qh-muted); font-size: 12px; font-weight: 400; line-height: 1.6; }
.body-fields input, .body-fields select { width: 100%; min-width: 0; height: 50px; padding: 0 14px; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-control); background: var(--qh-cream); color: var(--qh-berry); font-family: var(--qh-numeral); font-size: 19px; font-weight: 600; }
.body-fields input:hover, .body-fields select:hover { border-color: var(--qh-berry); }
.body-fields select { font-size: 16px; }
.input-with-unit { position: relative; display: block; }
.input-with-unit input { padding-right: 50px; }
.input-with-unit b { position: absolute; top: 50%; right: 16px; transform: translateY(-50%); color: var(--qh-muted); font-size: 12px; font-weight: 500; pointer-events: none; }
.goal-body { padding: 22px 20px 18px; }
.preset-field { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 0; margin: 0; padding: 0; border: 0; }
.preset-field legend { margin-bottom: 12px; font-size: 14px; font-weight: 600; }
.preset-option { display: flex; align-items: flex-start; gap: 9px; min-width: 0; padding: 16px 12px; border: 1px solid var(--qh-border); border-radius: 16px; cursor: pointer; background: var(--qh-cream); }
.preset-option:hover { border-color: var(--qh-berry); }
.preset-option.active { border-color: var(--qh-berry); background: var(--qh-oat); }
.preset-option:focus-within { outline: 2px solid var(--qh-berry); outline-offset: 3px; }
.preset-option input { flex: 0 0 18px; width: 18px; height: 18px; min-height: 18px; margin: 4px 0 0; accent-color: var(--qh-berry); }
.preset-copy { display: grid; min-width: 0; gap: 6px; }
.preset-copy > strong { font-size: 18px; }
.preset-copy > span { color: var(--qh-muted); font-size: 12px; }
.preset-copy .preset-range { margin-top: 4px; font-family: var(--qh-numeral); }
.preset-range b { display: block; color: var(--qh-berry); font-size: 23px; letter-spacing: -.035em; }
.target-note { margin: 14px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.8; }
.target-note strong { font-weight: 600; }
.formula-note > summary, .data-management > summary { font-size: 14px; }
.disclosure-body { padding: 4px 20px 16px; }
.disclosure-body p { color: var(--qh-muted); font-size: 13px; line-height: 1.8; margin: 12px 0 0; }
.form-actions { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 4px 0; }
.save-feedback { margin: 0; color: var(--qh-muted); font-size: 12px; line-height: 1.7; }
.primary-button { flex-shrink: 0; min-height: 46px; padding: 10px 24px; border: 0; border-radius: var(--qh-radius-pill); color: var(--qh-cream); background: var(--qh-berry); font-weight: 700; cursor: pointer; box-shadow: 0 3px 0 var(--qh-red); }
.primary-button:hover:not(:disabled) { background: var(--qh-brand-hover); }
button:disabled { opacity: .55; cursor: default; }
.form-fields:disabled { opacity: .7; }
.summary-content { padding: 18px 20px; }
.summary-intro, .summary-footnote { margin: 0; color: var(--qh-muted); font-size: 12px; line-height: 1.8; }
.profile-summary dl { margin: 2px 0 16px; }
.summary-row { padding: 18px 0; border-bottom: 1px solid var(--qh-border); }
.summary-row dt { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.metric-icon { width: 28px; height: 28px; }
.metric-icon .ui-icon { width: 17px; height: 17px; }
.flame-icon { color: var(--qh-red); background: color-mix(in srgb, var(--qh-yellow) 60%, var(--qh-cream)); }
.summary-row dd { display: flex; flex-wrap: wrap; align-items: baseline; gap: 5px 7px; margin: 8px 0 0 36px; font-family: var(--qh-numeral); }
.summary-row dd strong { font-size: 27px; letter-spacing: -.035em; }
.summary-row dd small { color: var(--qh-muted); font-size: 11px; }
.data-management { margin-top: 28px; }
.data-management > summary { color: var(--qh-muted); }
.data-management-body { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 20px; }
.data-management-body strong { font-size: 14px; }
.data-management-body p { margin: 6px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.8; }
.danger-link { flex-shrink: 0; min-height: 44px; padding: 8px 16px; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-pill); color: var(--qh-muted); background: var(--qh-cream); cursor: pointer; font-size: 13px; }
.danger-link:hover:not(:disabled) { color: var(--qh-berry); border-color: var(--qh-berry); background: var(--qh-oat); }
@media (max-width: 1100px) {
  .profile-layout { grid-template-columns: minmax(0, 1fr) 250px; gap: 18px; }
  .card-header { padding: 16px; }
  .card-header h2 { font-size: 18px; }
}
@media (max-width: 950px) {
  .profile-layout { grid-template-columns: minmax(0, 1fr); }
  .profile-summary dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
  .summary-row dd { margin-left: 0; }
}
@media (max-width: 760px) {
  .profile-page { padding: 22px 12px calc(96px + env(safe-area-inset-bottom)); }
  .profile-page--onboarding { padding-bottom: calc(32px + env(safe-area-inset-bottom)); }
  .page-header h1 { font-size: 30px; }
  .brand-seal { flex-basis: 48px; width: 48px; height: 48px; }
  .brand-seal .leaf-mark { width: 30px; height: 27px; }
  .body-fields { padding: 18px 16px; gap: 18px 14px; }
  .goal-body { padding: 18px 16px; }
  .form-actions { flex-direction: column-reverse; align-items: stretch; gap: 12px; }
  .save-feedback { text-align: center; }
  .primary-button { min-height: 48px; }
  .summary-content { padding: 16px; }
  .summary-row dd strong { font-size: 23px; }
  .data-management-body { flex-direction: column; align-items: flex-start; padding: 16px; gap: 14px; }
}
@media (max-width: 420px) {
  .page-header { gap: 12px; }
  .page-header h1 { font-size: 27px; }
  .body-fields { grid-template-columns: minmax(0, 1fr); }
  .preset-field { grid-template-columns: minmax(0, 1fr); }
  .preset-option { padding: 14px; }
  .preset-copy { width: 100%; grid-template-columns: minmax(0, 1fr) auto; align-items: baseline; gap: 4px 10px; }
  .preset-copy > strong { grid-column: 1; }
  .preset-copy > span { grid-column: 1; }
  .preset-copy .preset-range { grid-column: 2; grid-row: 1 / 3; text-align: right; }
  .preset-range b { font-size: 21px; }
  .profile-summary dl { grid-template-columns: minmax(0, 1fr); gap: 0; }
  .summary-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; }
  .summary-row dd { justify-content: flex-end; margin: 0; }
}
</style>
