<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import { api, type DeficitPreset, type ProfilePayload } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

withDefaults(defineProps<{ onboarding?: boolean }>(), { onboarding: false })
const emit = defineEmits<{ saved: [] }>()
const store = useQinghengStore()

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
    ? '约 0.25 kg/周 · 250–350 kcal/日'
    : '约 0.5 kg/周 · 500–600 kcal/日',
)

async function save() {
  await store.saveProfile({ ...form })
  emit('saved')
}

async function clearHistory() {
  const value = window.prompt('此操作会删除饮食、运动、每日体重和日汇总。请输入：清空全部历史记录')
  if (value !== '清空全部历史记录') return
  await store.mutate(() => api.clearHistory())
}

function selectPreset(value: DeficitPreset) {
  form.deficit_preset = value
}
</script>

<template>
  <main class="profile-page" :class="{ 'profile-page--onboarding': onboarding }">
    <section class="profile-card">
      <header class="profile-card__header">
        <div class="leaf-mark">叶</div>
        <div>
          <p class="eyebrow">{{ onboarding ? '开始使用轻衡' : '个人参数' }}</p>
          <h1>{{ onboarding ? '先建立你的能量基线' : '我的档案' }}</h1>
          <p>仅用于本机估算，不会创建账号或上传档案。</p>
        </div>
      </header>

      <form class="profile-form" @submit.prevent="save">
        <label>
          <span>年龄</span>
          <input v-model.number="form.age" type="number" min="18" max="64" required />
          <small>首版仅支持 18–64 岁健康成人</small>
        </label>
        <label>
          <span>生理性别</span>
          <select v-model="form.biological_sex" required>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
          <small>仅用于 Mifflin–St Jeor 公式</small>
        </label>
        <label>
          <span>身高</span>
          <div class="input-with-unit"><input v-model.number="form.height_cm" type="number" min="120" max="230" step="0.1" required /><b>cm</b></div>
        </label>
        <label>
          <span>当前体重</span>
          <div class="input-with-unit"><input v-model.number="form.current_weight_kg" type="number" min="30" max="300" step="0.1" required /><b>kg</b></div>
        </label>

        <fieldset class="preset-field">
          <legend>减脂档位</legend>
          <button type="button" :class="{ active: form.deficit_preset === 'gentle' }" @click="selectPreset('gentle')">
            <strong>温和</strong><span>更容易长期坚持</span>
          </button>
          <button type="button" :class="{ active: form.deficit_preset === 'standard' }" @click="selectPreset('standard')">
            <strong>标准</strong><span>缺口更明显</span>
          </button>
          <small>{{ presetCopy }}</small>
        </fieldset>

        <div class="formula-note">
          <strong>估算说明</strong>
          <p>静息消耗采用 Mifflin–St Jeor 公式，乘以 1.2 日常系数并展示约 ±10% 区间；运动单独记录。</p>
        </div>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="store.busy">
            {{ onboarding ? '完成建档并进入今日' : '保存档案' }}
          </button>
          <button v-if="!onboarding" class="danger-link" type="button" :disabled="store.busy" @click="clearHistory">清空历史记录</button>
        </div>
      </form>
    </section>

    <aside v-if="store.profile && !onboarding" class="profile-summary">
      <p class="eyebrow">当前估算</p>
      <div><span>BMI</span><strong>{{ store.profile.bmi }}</strong></div>
      <div><span>静息消耗</span><strong>{{ store.profile.rmr_kcal }} kcal</strong></div>
      <div><span>目标缺口</span><strong>{{ store.profile.target_deficit.low }}–{{ store.profile.target_deficit.high }} kcal</strong></div>
      <p>公式估算不能替代医疗、营养或运动专业意见。</p>
    </aside>
  </main>
</template>

<style scoped>
.profile-page { display: grid; grid-template-columns: minmax(0, 760px) 280px; gap: 24px; width: min(1080px, 100%); margin: 0 auto; padding: 34px; }
.profile-page--onboarding { min-height: 100%; align-items: center; grid-template-columns: minmax(0, 760px); justify-content: center; }
.profile-card, .profile-summary { border: 1px solid var(--qh-border); border-radius: 24px; background: var(--qh-card); box-shadow: var(--qh-shadow); }
.profile-card { padding: clamp(24px, 4vw, 42px); }
.profile-card__header { display: flex; gap: 18px; align-items: flex-start; margin-bottom: 34px; }
.profile-card__header h1 { margin: 3px 0 8px; font-size: 30px; letter-spacing: -.04em; }
.profile-card__header p { margin: 0; color: var(--qh-muted); }
.leaf-mark { display: grid; flex: 0 0 48px; width: 48px; height: 48px; place-items: center; border-radius: 15px 5px 15px 5px; color: white; background: var(--qh-green); font-weight: 800; }
.eyebrow { margin: 0; color: var(--qh-green-dark) !important; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.profile-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
label { display: grid; gap: 8px; color: var(--qh-text); font-weight: 700; }
label small, .preset-field small { color: var(--qh-muted); font-size: 12px; font-weight: 500; }
input, select { width: 100%; height: 46px; padding: 0 13px; border: 1px solid var(--qh-border-strong); border-radius: 12px; color: var(--qh-text); background: white; }
.input-with-unit { position: relative; }
.input-with-unit input { padding-right: 45px; }
.input-with-unit b { position: absolute; top: 14px; right: 13px; color: var(--qh-muted); font-size: 12px; }
.preset-field { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; grid-column: 1 / -1; margin: 4px 0 0; padding: 0; border: 0; }
.preset-field legend { margin-bottom: 10px; font-weight: 800; }
.preset-field button { display: grid; gap: 3px; padding: 15px; border: 1px solid var(--qh-border); border-radius: 14px; text-align: left; color: var(--qh-text); background: white; cursor: pointer; }
.preset-field button span { color: var(--qh-muted); font-size: 12px; }
.preset-field button.active { border-color: var(--qh-green); background: var(--qh-sage-soft); box-shadow: 0 0 0 2px rgb(75 125 66 / 10%); }
.preset-field > small { grid-column: 1 / -1; }
.formula-note { grid-column: 1 / -1; padding: 15px 17px; border-radius: 14px; background: var(--qh-ivory-strong); }
.formula-note p { margin: 5px 0 0; color: var(--qh-muted); font-size: 13px; line-height: 1.6; }
.form-actions { display: flex; grid-column: 1 / -1; align-items: center; justify-content: space-between; gap: 16px; margin-top: 6px; }
.primary-button { min-height: 46px; padding: 0 22px; border: 0; border-radius: 13px; color: white; background: var(--qh-green); font-weight: 800; cursor: pointer; }
.primary-button:disabled { opacity: .55; cursor: wait; }
.danger-link { border: 0; color: #a24a3f; background: transparent; cursor: pointer; }
.profile-summary { align-self: start; padding: 24px; }
.profile-summary > div { display: grid; gap: 5px; padding: 18px 0; border-bottom: 1px solid var(--qh-border); }
.profile-summary span { color: var(--qh-muted); font-size: 13px; }
.profile-summary strong { font-size: 20px; }
.profile-summary > p:last-child { margin: 20px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.6; }
@media (max-width: 850px) { .profile-page { grid-template-columns: 1fr; padding: 20px; } .profile-summary { display: none; } }
@media (max-width: 560px) { .profile-form { grid-template-columns: 1fr; } .preset-field, .formula-note, .form-actions { grid-column: 1; } .preset-field { grid-template-columns: 1fr; } .profile-card { padding: 22px; } .form-actions { align-items: stretch; flex-direction: column; } }
</style>
