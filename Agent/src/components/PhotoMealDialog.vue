<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { vDialog } from '@/utils/dialog'
import { api, type KcalRange, type Meal, type MealType } from '@/api/qingheng'
import { ApiError } from '@/api/client'
import { useQinghengStore } from '@/stores/qingheng'
import UiIcon from './UiIcon.vue'
import MealRecordCard from './MealRecordCard.vue'

const emit = defineEmits<{ close: []; manual: [] }>()
const store = useQinghengStore()
const mealType = ref<MealType>('lunch')
const customMealName = ref('')
const file = ref<File | null>(null)
const preview = ref('')
const localError = ref('')
const submitting = ref(false)
const uncertain = ref(false)
const result = ref<Meal | null>(null)
const resultHeading = ref<HTMLElement>()
const fileInput = ref<HTMLInputElement>()
const cameraInput = ref<HTMLInputElement>()
const locked = computed(() => submitting.value || store.busy || uncertain.value)
const fileSize = computed(() => !file.value ? '' : file.value.size >= 1024 * 1024
  ? `${(file.value.size / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(file.value.size / 1024))} KB`)
const formatRange = (value: KcalRange) => value.low === value.high ? value.low.toLocaleString('zh-CN') : `${value.low.toLocaleString('zh-CN')}–${value.high.toLocaleString('zh-CN')}`

function close() {
  if (!submitting.value) emit('close')
}
function clearPhoto() {
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''
  file.value = null
}
function selectFile(event: Event) {
  const input = event.target as HTMLInputElement
  const selected = input.files?.[0]
  input.value = ''
  if (!selected || locked.value) return
  localError.value = ''
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) && !(selected.type === '' && /\.(jpe?g|png|webp)$/i.test(selected.name))) {
    localError.value = '请选择 JPEG、PNG 或 WebP 照片。'
    return
  }
  if (!selected.size || selected.size > 10 * 1024 * 1024) {
    localError.value = selected.size ? '照片不能超过 10 MB，请选择较小的图片。' : '这张照片是空文件，请重新选择。'
    return
  }
  clearPhoto()
  file.value = selected
  preview.value = URL.createObjectURL(selected)
}
function previewFailed() {
  clearPhoto()
  localError.value = '无法预览这张照片，请重新选择 JPEG、PNG 或 WebP 图片。'
}
async function submit() {
  if (!file.value || locked.value || result.value) return
  if (mealType.value === 'custom' && !customMealName.value.trim()) {
    localError.value = '请填写自定义餐次名称'
    return
  }
  localError.value = ''
  submitting.value = true
  const selectedFile = file.value
  const selectedType = mealType.value
  const selectedName = selectedType === 'custom' ? customMealName.value.trim() : null
  try {
    await store.mutate(async () => {
      result.value = await api.createPhotoMeal(selectedFile, selectedType, selectedName)
    })
  } catch (error) {
    uncertain.value = error instanceof ApiError && (error.status === 0 || [500, 502, 504].includes(error.status))
    localError.value = uncertain.value
      ? '暂时无法确认是否已入账。请先查看今日餐食，确认没有这条记录后再重新上传。'
      : error instanceof Error ? error.message : '识别失败，请重试或改用手动记录。'
  } finally {
    submitting.value = false
  }
  if (result.value) {
    await nextTick()
    resultHeading.value?.focus()
  }
}
async function checkRecords() {
  if (store.busy) return
  await store.reloadToday()
  close()
}
onBeforeUnmount(clearPhoto)
</script>

<template>
  <div v-dialog="close" class="modal-backdrop" @mousedown.self="close">
    <section class="photo-dialog" role="dialog" aria-modal="true" aria-labelledby="photo-dialog-title">
      <header class="dialog-header">
        <div><p class="eyebrow">{{ result && !submitting ? '整餐记录' : '拍照记录' }}</p><h2 id="photo-dialog-title">{{ result && !submitting ? '这一餐，记好了' : '把这一餐，轻松记下' }}</h2><p class="header-copy">{{ result && !submitting ? '已加入餐食记录，可以核对食物与份量。' : '上传整餐照片，识别成功后自动入账。' }}</p></div>
        <button class="close-button" type="button" aria-label="关闭" :disabled="submitting" @click="close">×</button>
      </header>

      <div class="dialog-content">
        <template v-if="result && !submitting">
          <div class="result-banner" role="status"><span class="success-mark" aria-hidden="true">✓</span><div><h3 ref="resultHeading" tabindex="-1">{{ result.display_name }}已入账</h3><p>{{ result.recorded_date }} · {{ result.items.length }} 项食物</p></div><span class="result-kcal"><strong>{{ formatRange(result.kcal) }}</strong><small>kcal</small></span></div>
          <MealRecordCard :meal="result" readonly open />
          <p class="result-note">热量与份量为估算值。若识别有误，可在今日餐食中删除这条记录后重新记录。</p>
        </template>
        <template v-else>
          <input ref="fileInput" class="file-input" type="file" tabindex="-1" aria-label="选择整餐照片" :disabled="locked" accept="image/jpeg,image/png,image/webp" @change="selectFile" />
          <input ref="cameraInput" class="file-input" type="file" tabindex="-1" aria-label="拍摄整餐照片" :disabled="locked" accept="image/jpeg,image/png,image/webp" capture="environment" @change="selectFile" />
          <section v-if="!file" class="upload-area">
            <span class="camera-mark"><UiIcon name="camera" /></span><h3>让整餐完整入镜</h3><p>光线清晰，尽量拍全食物与餐具。</p>
            <div class="upload-actions"><button type="button" class="primary choose-photo" :disabled="locked" @click="fileInput?.click()">选择照片</button><button type="button" class="secondary take-photo" :disabled="locked" @click="cameraInput?.click()"><UiIcon name="camera" />拍一张</button></div>
            <small>JPEG、PNG、WebP · 最大 10 MB</small>
          </section>
          <section v-else class="photo-preview" aria-label="所选照片预览">
            <div class="preview-frame"><img :src="preview" alt="准备识别的整餐照片" @error="previewFailed" /></div>
            <div class="preview-caption"><div><strong :title="file.name">{{ file.name }}</strong><small>{{ fileSize }} · 请确认食物完整、清晰</small></div><button type="button" class="secondary reselect" :disabled="locked" @click="fileInput?.click()">重新选择</button></div>
          </section>

          <div v-if="submitting" class="processing-state" role="status" aria-live="polite"><span class="processing-dot" aria-hidden="true"></span><div><strong>正在识别并记录这一餐…</strong><p>正在估算食物和份量，完成后会展示入账结果。请稍候。</p></div></div>
          <fieldset class="meal-field" :disabled="locked"><legend>这是哪一餐？</legend><div class="meal-types"><label v-for="option in [['breakfast', '早餐'], ['lunch', '午餐'], ['dinner', '晚餐'], ['custom', '自定义']] as const" :key="option[0]" :class="{ active: mealType === option[0] }"><input v-model="mealType" type="radio" name="photo-meal-type" :value="option[0]" /><span>{{ option[1] }}</span></label></div><label v-if="mealType === 'custom'" class="custom-name"><span>餐次名称</span><input v-model="customMealName" class="name-input" maxlength="40" placeholder="例如：下午加餐" /></label></fieldset>
          <div class="privacy-note"><UiIcon name="leaf" /><div><strong>本服务不保存原图</strong><p>照片会发送至模型服务进行识别，仅保留结构化餐食记录。</p></div></div>
          <div v-if="localError" class="form-error" role="alert"><strong>{{ uncertain ? '入账状态待确认' : '暂时未能完成' }}</strong><p>{{ localError }}</p></div>
        </template>
      </div>

      <footer class="dialog-footer">
        <template v-if="result && !submitting"><span class="footer-note">已保存，无需重复提交</span><button type="button" class="primary" @click="close">完成，返回今日</button></template>
        <template v-else-if="uncertain"><span class="footer-note">先核对记录，避免重复入账</span><button type="button" class="primary" :disabled="store.busy" @click="checkRecords">查看今日餐食</button></template>
        <template v-else><button type="button" class="manual-link" :disabled="locked" @click="emit('manual')">改用手动记录</button><button type="button" class="primary submit-photo" :disabled="!file || locked || (mealType === 'custom' && !customMealName.trim())" @click="submit">{{ submitting ? '正在识别…' : '识别并自动入账' }}</button></template>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: var(--qh-overlay); backdrop-filter: blur(4px); }
.photo-dialog { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; width: min(620px, 100%); max-height: calc(100vh - 40px); max-height: calc(100dvh - 40px); overflow: hidden; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: 24px; background: var(--qh-cream); box-shadow: var(--qh-shadow); }
.dialog-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 22px 24px; background: var(--qh-oat); border-bottom: 1px solid var(--qh-border); }
.eyebrow { margin: 0 0 5px; color: var(--qh-muted); font-size: 12px; }
h2 { margin: 0; font-size: 26px; letter-spacing: -.03em; line-height: 1.4; }
.header-copy { margin: 7px 0 0; color: var(--qh-muted); font-size: 13px; line-height: 1.6; }
.close-button { flex: 0 0 40px; width: 40px; height: 40px; border: 0; border-radius: 50%; color: var(--qh-muted); background: var(--qh-cream); font-size: 25px; cursor: pointer; }
.dialog-content { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 22px 24px; scroll-padding-block: 20px; }
.file-input { display: none; }
.upload-area { display: grid; justify-items: center; gap: 10px; padding: 24px 16px; border: 1px dashed var(--qh-berry); border-radius: 20px; background: var(--qh-oat); text-align: center; }
.camera-mark { display: grid; place-items: center; width: 56px; height: 56px; border-radius: 50%; color: var(--qh-cream); background: var(--qh-berry); }
.camera-mark .ui-icon { width: 27px; height: 27px; }
.upload-area h3 { margin: 2px 0 0; font-size: 19px; }
.upload-area p { margin: 0; color: var(--qh-muted); font-size: 13px; }
.upload-area small { color: var(--qh-muted); font-size: 11px; }
.upload-actions { display: flex; gap: 10px; margin: 4px 0; }
.primary, .secondary { min-height: 44px; padding: 10px 18px; border-radius: var(--qh-radius-pill); font-size: 14px; font-weight: 600; cursor: pointer; }
.primary { border: 1px solid var(--qh-berry); background: var(--qh-berry); color: var(--qh-cream); }
.primary:not(:disabled):hover { background: var(--qh-brand-hover); }
.secondary { border: 1px solid var(--qh-border); background: var(--qh-cream); color: var(--qh-berry); }
.secondary:not(:disabled):hover { border-color: var(--qh-berry); }
.take-photo { display: flex; align-items: center; gap: 7px; }
.take-photo .ui-icon { width: 18px; height: 18px; }
.photo-preview { border: 1px solid var(--qh-border); border-radius: 20px; overflow: hidden; background: var(--qh-oat); }
.preview-frame { display: grid; place-items: center; height: clamp(150px, 28vh, 240px); }
.preview-frame img { display: block; width: 100%; height: 100%; min-height: 0; object-fit: contain; }
.preview-caption { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; background: var(--qh-cream); border-top: 1px solid var(--qh-border); }
.preview-caption > div { display: grid; gap: 4px; min-width: 0; }
.preview-caption strong { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.preview-caption small { color: var(--qh-muted); font-size: 11px; }
.reselect { flex-shrink: 0; padding: 8px 12px; font-size: 12px; }
.meal-field { margin: 22px 0 0; padding: 0; border: 0; min-width: 0; }
.meal-field legend { margin-bottom: 10px; font-size: 14px; font-weight: 600; }
.meal-types { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.meal-types label { position: relative; display: grid; place-items: center; min-height: 44px; border: 1px solid var(--qh-border); border-radius: 12px; color: var(--qh-muted); cursor: pointer; font-size: 14px; }
.meal-types label.active { color: var(--qh-berry); border-color: var(--qh-berry); background: var(--qh-oat); font-weight: 700; }
.meal-types label:focus-within { outline: 2px solid var(--qh-berry); outline-offset: 2px; }
.meal-types input { position: absolute; opacity: 0; width: 1px; height: 1px; min-height: 0; margin: 0; }
.custom-name { display: grid; gap: 7px; margin-top: 12px; font-size: 12px; }
.name-input { width: 100%; min-width: 0; min-height: 46px; padding: 10px 12px; border: 1px solid var(--qh-border); border-radius: 12px; background: var(--qh-cream); color: var(--qh-berry); font-size: 16px; }
.privacy-note { display: flex; align-items: start; gap: 9px; margin-top: 18px; padding: 12px; border-radius: 12px; background: var(--qh-oat); }
.privacy-note .ui-icon { width: 18px; height: 18px; margin-top: 2px; }
.privacy-note strong { font-size: 12px; font-weight: 600; }
.privacy-note p { margin: 4px 0 0; color: var(--qh-muted); font-size: 11px; line-height: 1.7; }
.processing-state { display: flex; align-items: start; gap: 10px; margin-top: 16px; padding: 14px; border: 1px solid var(--qh-border); border-radius: 14px; background: var(--qh-oat); }
.processing-state strong { font-size: 13px; }
.processing-state p { margin: 4px 0 0; font-size: 12px; line-height: 1.7; color: var(--qh-muted); }
.processing-dot { flex: 0 0 10px; width: 10px; height: 10px; margin-top: 6px; border-radius: 50%; background: var(--qh-berry); }
@media (prefers-reduced-motion: no-preference) { .processing-dot { animation: breathe 1.4s ease-in-out infinite alternate; } @keyframes breathe { to { opacity: .25; } } }
.form-error { margin-top: 16px; padding: 12px 14px; border: 1px solid var(--qh-border); border-radius: 12px; background: var(--qh-oat); }
.form-error strong { font-size: 13px; }
.form-error p { margin: 4px 0 0; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.dialog-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--qh-border); background: var(--qh-oat); }
.manual-link { padding: 8px 0; min-height: 44px; border: 0; color: var(--qh-muted); background: transparent; font-size: 13px; cursor: pointer; }
.footer-note { color: var(--qh-muted); font-size: 12px; }
.result-banner { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 16px; margin-bottom: 16px; border-radius: 18px; background: var(--qh-oat); }
.success-mark { display: grid; place-items: center; flex: 0 0 38px; width: 38px; height: 38px; border-radius: 50%; background: var(--qh-mint); font-size: 23px; }
.result-banner h3 { margin: 0; font-size: 18px; }
.result-banner p { margin: 5px 0 0; font-size: 12px; color: var(--qh-muted); }
.result-kcal { display: flex; align-items: baseline; flex-wrap: wrap; gap: 5px; margin-left: auto; font-family: var(--qh-numeral); }
.result-kcal strong { font-size: 25px; }
.result-kcal small { font-size: 11px; }
.result-note { margin: 14px 0 0; color: var(--qh-muted); font-size: 12px; line-height: 1.8; }
button:disabled { cursor: default; opacity: .5; }
.meal-field:disabled { opacity: .6; }
@media (max-width: 760px) {
  .modal-backdrop { align-items: end; padding: 0; }
  .photo-dialog { width: 100%; max-height: 94vh; max-height: 94dvh; border-radius: 22px 22px 0 0; }
  .dialog-header { padding: 18px 16px; gap: 10px; }
  h2 { font-size: 22px; }
  .close-button { flex-basis: 44px; width: 44px; height: 44px; }
  .dialog-content { padding: 16px; }
  .dialog-footer { padding: 12px 16px calc(12px + env(safe-area-inset-bottom)); }
  .preview-frame { height: clamp(140px, 25dvh, 210px); }
  .meal-types { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .result-kcal { margin-left: 50px; }
}
@media (max-width: 360px) {
  .dialog-footer { flex-wrap: wrap; }
  .dialog-footer .primary { flex: 1 1 auto; }
  .footer-note { flex-basis: 100%; }
  .preview-caption { flex-wrap: wrap; }
  .preview-caption > div { width: 100%; }
}
</style>
