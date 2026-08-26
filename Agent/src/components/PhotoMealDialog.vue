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
    await store.mutate(() =>
      api.createPhotoMeal(
        file.value!,
        mealType.value,
        mealType.value === 'custom' ? customMealName.value.trim() : null,
      ),
    )
    emit('close')
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '识别失败'
  }
}
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="emit('close')">
    <section class="photo-dialog" role="dialog" aria-modal="true">
      <header>
        <div>
          <p>拍照估算</p>
          <h2>上传一张整餐照片</h2>
          <span>识别食物、估算份量，并自动加入今天。</span>
        </div>
        <button aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <label class="drop-zone">
        <input type="file" accept="image/jpeg,image/png,image/webp" @change="selectFile" />
        <span class="camera"><i /></span>
        <strong>{{ file ? file.name : '打开相机或选择照片' }}</strong>
        <small>{{
          file ? '照片已就绪，可继续确认餐次' : '让整餐完整入镜 · 支持 JPEG、PNG、WebP'
        }}</small>
        <b>{{ file ? '重新选择' : '选择照片' }}</b>
      </label>
      <p class="field-label"><span>接下来</span> 这是哪一餐？</p>
      <div class="meal-types">
        <button
          v-for="option in [
            ['breakfast', '早餐'],
            ['lunch', '午餐'],
            ['dinner', '晚餐'],
            ['custom', '自定义'],
          ] as const"
          :key="option[0]"
          :class="{ active: mealType === option[0] }"
          @click="mealType = option[0]"
        >
          {{ option[1] }}
        </button>
      </div>
      <input
        v-if="mealType === 'custom'"
        v-model="customMealName"
        class="name-input"
        maxlength="40"
        placeholder="自定义餐次名称"
      />
      <div class="privacy-note">
        <strong><i /> 原图不会保存</strong>
        <p>服务端会在内存中完成验证与识别，之后只保留结构化的餐食记录。</p>
      </div>
      <p v-if="localError" class="form-error">{{ localError }}</p>
      <footer>
        <button class="secondary" @click="emit('close')">取消</button
        ><button class="primary" :disabled="!file || store.busy" @click="submit">
          {{ store.busy ? '正在识别…' : '识别并自动入账' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  z-index: 40;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgb(33 38 30 / 38%);
  backdrop-filter: blur(4px);
}
.photo-dialog {
  width: min(540px, 100%);
  padding: 28px;
  border: 1px solid var(--qh-border);
  border-radius: 28px 9px 28px 9px;
  background: var(--qh-card);
  box-shadow: 0 28px 80px rgb(18 56 42 / 25%);
}
header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
header p,
h2 {
  margin: 0;
}
header p {
  color: var(--qh-green-dark);
  font-family: var(--qh-data);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
}
h2 {
  margin-top: 6px;
  font-size: 27px;
}
header div > span {
  display: block;
  margin-top: 6px;
  color: var(--qh-muted);
  font-size: 12px;
}
header button {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 12px;
  color: var(--qh-muted);
  background: var(--qh-sage-soft);
  font-size: 25px;
  cursor: pointer;
}
.field-label {
  margin: 18px 0 9px;
  font-size: 12px;
  font-weight: 800;
}
.field-label span {
  margin-right: 6px;
  color: var(--qh-muted);
  font-family: var(--qh-data);
  font-size: 9px;
  letter-spacing: 0.08em;
}
.meal-types {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.meal-types button {
  height: 41px;
  border: 1px solid var(--qh-border);
  border-radius: 12px 5px 12px 5px;
  color: var(--qh-text);
  background: white;
  cursor: pointer;
}
.meal-types button.active {
  border-color: var(--qh-green);
  color: var(--qh-green-dark);
  background: var(--qh-sage-soft);
  font-weight: 800;
  box-shadow: inset 0 0 0 1px rgb(45 106 79 / 8%);
}
.name-input {
  width: 100%;
  height: 43px;
  margin-top: 10px;
  padding: 0 12px;
  border: 1px solid var(--qh-border-strong);
  border-radius: 11px;
}
.drop-zone {
  display: grid;
  position: relative;
  place-items: center;
  gap: 8px;
  margin-top: 22px;
  padding: 30px 20px 24px;
  border: 1.5px dashed #89aa94;
  border-radius: 22px 7px 22px 7px;
  background: linear-gradient(145deg, #e8f1ea, #f4f8f4);
  text-align: center;
  cursor: pointer;
}
.drop-zone:hover {
  border-color: var(--qh-green);
  background: #edf5ee;
}
.drop-zone input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}
.drop-zone small {
  color: var(--qh-muted);
}
.drop-zone > b {
  margin-top: 7px;
  padding: 8px 14px;
  border-radius: 11px 4px 11px 4px;
  color: white;
  background: var(--qh-green-ink);
  font-size: 11px;
}
.camera {
  position: relative;
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  margin-bottom: 4px;
  border: 1px solid #b7d1be;
  border-radius: 50%;
  background: white;
}
.camera::before {
  width: 27px;
  height: 20px;
  border: 2px solid var(--qh-green);
  border-radius: 5px;
  content: '';
}
.camera::after {
  position: absolute;
  top: 15px;
  width: 12px;
  height: 5px;
  border: 2px solid var(--qh-green);
  border-bottom: 0;
  border-radius: 3px 3px 0 0;
  content: '';
}
.camera i {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 2px solid var(--qh-green);
  border-radius: 50%;
}
.privacy-note {
  margin-top: 16px;
  padding: 13px 15px;
  border-radius: 14px 5px 14px 5px;
  background: var(--qh-ivory-strong);
}
.privacy-note strong {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
}
.privacy-note strong i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--qh-green);
}
.privacy-note p {
  margin: 5px 0 0;
  color: var(--qh-muted);
  font-size: 11px;
  line-height: 1.5;
}
.form-error {
  padding: 10px 12px;
  border-radius: 10px;
  color: #8f3f35;
  background: #fff0ed;
  font-size: 13px;
}
footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
footer button {
  min-height: 43px;
  padding: 0 17px;
  border-radius: 13px 5px 13px 5px;
  font-weight: 800;
  cursor: pointer;
}
.secondary {
  border: 1px solid var(--qh-border);
  background: white;
}
.primary {
  border: 0;
  color: white;
  background: var(--qh-green-ink);
}
.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 560px) {
  .modal-backdrop {
    align-items: end;
    padding: 0;
  }
  .photo-dialog {
    padding: 23px 20px;
    border-radius: 24px 24px 0 0;
  }
  .meal-types {
    grid-template-columns: repeat(2, 1fr);
  }
  .drop-zone {
    padding-block: 25px 21px;
  }
}
</style>
