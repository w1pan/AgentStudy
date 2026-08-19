<script setup lang="ts">
import { ref } from 'vue'

import { api, type MealType } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

const emit = defineEmits<{ close: [] }>()
const store = useQinghengStore()
const mealType = ref<MealType>('lunch')
const customMealName = ref('')
const file = ref<File | null>(null)
const localError = ref('')

function selectFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
}

async function submit() {
  if (!file.value) return
  if (mealType.value === 'custom' && !customMealName.value.trim()) {
    localError.value = '请填写自定义餐次名称'
    return
  }
  localError.value = ''
  try {
    await store.mutate(() => api.createPhotoMeal(file.value!, mealType.value, mealType.value === 'custom' ? customMealName.value.trim() : null))
    emit('close')
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '识别失败'
  }
}
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="emit('close')">
    <section class="photo-dialog" role="dialog" aria-modal="true">
      <header><div><p>AI 拍照估算</p><h2>先选餐次，再上传照片</h2></div><button @click="emit('close')">×</button></header>
      <div class="meal-types">
        <button v-for="option in ([['breakfast','早餐'],['lunch','午餐'],['dinner','晚餐'],['custom','自定义']] as const)" :key="option[0]" :class="{ active: mealType === option[0] }" @click="mealType = option[0]">{{ option[1] }}</button>
      </div>
      <input v-if="mealType === 'custom'" v-model="customMealName" class="name-input" maxlength="40" placeholder="自定义餐次名称" />
      <label class="drop-zone">
        <input type="file" accept="image/jpeg,image/png,image/webp" @change="selectFile" />
        <span class="camera">▣</span>
        <strong>{{ file ? file.name : '选择一张整餐照片' }}</strong>
        <small>支持 JPEG（含微信 MPO 容器）、PNG、WebP，最大 10 MiB</small>
      </label>
      <div class="privacy-note"><strong>照片不会保存</strong><p>服务端会验证并在内存中重编码，识别完成后只保留结构化餐食记录。</p></div>
      <p v-if="localError" class="form-error">{{ localError }}</p>
      <footer><button class="secondary" @click="emit('close')">取消</button><button class="primary" :disabled="!file || store.busy" @click="submit">{{ store.busy ? '正在识别…' : '识别并自动入账' }}</button></footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(33 38 30 / 38%); backdrop-filter: blur(4px); }
.photo-dialog { width: min(520px, 100%); padding: 26px; border: 1px solid var(--qh-border); border-radius: 24px; background: var(--qh-card); box-shadow: 0 28px 80px rgb(30 45 26 / 22%); }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; } header p, h2 { margin: 0; } header p { color: var(--qh-green-dark); font-size: 12px; font-weight: 800; } h2 { margin-top: 5px; font-size: 24px; }
header button { width: 38px; height: 38px; border: 0; border-radius: 12px; color: var(--qh-muted); background: var(--qh-sage-soft); font-size: 25px; cursor: pointer; }
.meal-types { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 22px; }.meal-types button { height: 41px; border: 1px solid var(--qh-border); border-radius: 11px; color: var(--qh-text); background: white; cursor: pointer; }.meal-types button.active { border-color: var(--qh-green); color: var(--qh-green-dark); background: var(--qh-sage-soft); font-weight: 800; }
.name-input { width: 100%; height: 43px; margin-top: 10px; padding: 0 12px; border: 1px solid var(--qh-border-strong); border-radius: 11px; }
.drop-zone { display: grid; place-items: center; gap: 8px; margin-top: 18px; padding: 35px 20px; border: 1.5px dashed #9db698; border-radius: 18px; background: var(--qh-sage-soft); text-align: center; cursor: pointer; }.drop-zone input { position: absolute; width: 1px; height: 1px; opacity: 0; }.drop-zone small { color: var(--qh-muted); }.camera { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 50%; color: white; background: var(--qh-green); font-size: 24px; }
.privacy-note { margin-top: 16px; padding: 14px 16px; border-radius: 13px; background: var(--qh-ivory-strong); }.privacy-note p { margin: 5px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.5; }
.form-error { padding: 10px 12px; border-radius: 10px; color: #8f3f35; background: #fff0ed; font-size: 13px; }
footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; } footer button { min-height: 43px; padding: 0 17px; border-radius: 12px; font-weight: 800; cursor: pointer; }.secondary { border: 1px solid var(--qh-border); background: white; }.primary { border: 0; color: white; background: var(--qh-green); }.primary:disabled { opacity: .5; cursor: not-allowed; }
@media (max-width: 560px) { .modal-backdrop { align-items: end; padding: 0; }.photo-dialog { border-radius: 22px 22px 0 0; }.meal-types { grid-template-columns: repeat(2, 1fr); } }
</style>
