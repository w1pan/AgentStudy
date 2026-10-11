<script setup lang="ts">
import { vDialog } from '@/utils/dialog'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  api,
  type FoodTemplate,
  type ManualMealItemPayload,
  type Meal,
  type MealType,
} from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'
import { ApiError } from '@/api/client'
import UiIcon from './UiIcon.vue'

const props = defineProps<{ meal?: Meal | null }>()
const emit = defineEmits<{ close: [] }>()
const store = useQinghengStore()

interface DraftItem extends ManualMealItemPayload {
  key: string
  displayName: string
  units: string[]
  source: string
}

const mealType = ref<MealType>(props.meal?.meal_type || 'breakfast')
const customMealName = ref(props.meal?.custom_meal_name || '')
const recordedTime = ref((props.meal?.recorded_time || new Date().toTimeString().slice(0, 5)).slice(0, 5))
const query = ref('')
const results = ref<FoodTemplate[]>([])
const searching = ref(false)
const searched = ref(false)
const searchError = ref('')
const customError = ref('')
const feedback = ref('')
const submitting = ref(false)
const uncertain = ref(false)
const locked = computed(() => submitting.value || store.busy || uncertain.value)
let searchVersion = 0
const customName = ref('')
const customQuantity = ref(1)
const customUnit = ref('份')
const customLow = ref(0)
const customHigh = ref(0)
const localError = ref('')
// Draft keys only identify rows in this dialog; they are never sent to the API.
let draftItemSequence = 0

const items = ref<DraftItem[]>(
  (props.meal?.items || []).map((item) => ({
    key: item.id,
    template_id: item.template_id || undefined,
    name: item.template_id ? undefined : item.name,
    quantity: item.quantity,
    unit: item.unit,
    kcal: item.template_id ? undefined : { ...item.kcal },
    displayName: item.name,
    units: [item.unit],
    source: item.estimate_source === 'template' ? '内置模板' : '用户填写',
  })),
)

const validQuantity = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value > 0 && value <= 5000
const validKcal = (value: unknown) => typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 20000
const draftError = computed(() => items.value.some(item => !validQuantity(item.quantity))
  ? '请为每项食物填写大于 0、不超过 5000 的数量。'
  : items.value.some(item => item.kcal && (!validKcal(item.kcal.low) || !validKcal(item.kcal.high) || item.kcal.high < item.kcal.low))
    ? '请检查食物总热量：填写 0–20000 的整数，上限不能小于下限。' : '')
const canSubmit = computed(() => items.value.length > 0 && items.value.length <= 20 && !draftError.value
  && /^([01]\d|2[0-3]):[0-5]\d$/.test(recordedTime.value)
  && (mealType.value !== 'custom' || customMealName.value.trim()))

watch(query, () => {
  searchVersion++
  results.value = []
  searching.value = false
  searched.value = false
  searchError.value = ''
}, { flush: 'sync' })

async function search() {
  if (!query.value.trim() || locked.value) return
  const version = ++searchVersion
  searching.value = true
  searched.value = false
  searchError.value = ''
  results.value = []
  try {
    const response = await api.searchFoodTemplates(query.value.trim())
    if (version !== searchVersion) return
    results.value = response
    searched.value = true
  } catch (error) {
    if (version === searchVersion) searchError.value = error instanceof Error ? error.message : '搜索失败，请重试'
  } finally {
    if (version === searchVersion) searching.value = false
  }
}

function addTemplate(template: FoodTemplate) {
  if (locked.value || items.value.length >= 20) return
  const units = Object.keys(template.units)
  const preferred = units.find((unit) => unit !== '克') || '克'
  items.value.push({
    key: `draft-${++draftItemSequence}`,
    template_id: template.id,
    quantity: preferred === '克' ? 100 : 1,
    unit: preferred,
    displayName: template.name,
    units,
    source: `${template.source_name} · ${template.source_version}`,
  })
  feedback.value = `已添加${template.name}，本餐共 ${items.value.length} 项。`
}

function addCustom() {
  if (locked.value || items.value.length >= 20) return
  customError.value = ''
  if (!customName.value.trim() || !customUnit.value.trim() || !validQuantity(customQuantity.value)
    || !validKcal(customLow.value) || !validKcal(customHigh.value) || customHigh.value < customLow.value) {
    customError.value = '请填写名称、单位和有效数量；总热量需为 0–20000 的整数，且上限不小于下限。'
    return
  }
  items.value.push({
    key: `draft-${++draftItemSequence}`,
    name: customName.value.trim(),
    quantity: customQuantity.value,
    unit: customUnit.value.trim(),
    kcal: { low: customLow.value, high: customHigh.value },
    displayName: customName.value.trim(),
    units: [customUnit.value.trim()],
    source: '用户填写 · 本次记录',
  })
  feedback.value = `已添加${customName.value.trim()}，本餐共 ${items.value.length} 项。`
  customName.value = ''
  customLow.value = 0
  customHigh.value = 0
}

async function submit() {
  if (!canSubmit.value || locked.value) return
  localError.value = ''
  const payload = {
    meal_type: mealType.value,
    custom_meal_name: mealType.value === 'custom' ? customMealName.value.trim() : null,
    recorded_time: recordedTime.value,
    items: items.value.map(({ template_id, name, quantity, unit, kcal }) => ({
      template_id,
      name,
      quantity,
      unit,
      kcal: kcal ? { ...kcal } : undefined,
    })),
  }
  submitting.value = true
  try {
    await store.mutate(() =>
      props.meal ? api.updateManualMeal(props.meal.id, payload) : api.createManualMeal(payload),
    )
    store.notifySuccess(props.meal ? '餐食修改已保存' : '这一餐已保存')
    emit('close')
  } catch (error) {
    uncertain.value = !props.meal && error instanceof ApiError && (error.status === 0 || [500, 502, 504].includes(error.status))
    localError.value = uncertain.value ? '暂时无法确认是否已保存。请先查看今日餐食，确认没有这条记录后再重新添加。'
      : error instanceof Error ? error.message : '保存失败，请重试'
  } finally {
    submitting.value = false
  }
}

function close() { if (!submitting.value) emit('close') }
function removeItem(item: DraftItem) {
  if (locked.value) return
  items.value = items.value.filter(entry => entry.key !== item.key)
  feedback.value = `已移除${item.displayName}，本餐共 ${items.value.length} 项。`
}
async function checkRecords() {
  if (store.busy) return
  await store.reloadToday()
  close()
}
onBeforeUnmount(() => { searchVersion++ })
</script>

<template>
  <div v-dialog="close" class="modal-backdrop" @mousedown.self="close">
    <section class="dialog meal-dialog" role="dialog" aria-modal="true" aria-labelledby="manual-meal-title">
      <header class="dialog-header"><div><p class="eyebrow">手动记录</p><h2 id="manual-meal-title">{{ meal ? '调整这一餐' : '一餐一笔，慢慢记录' }}</h2><p class="header-copy">搜索食物、填写份量，确认后保存整餐。</p></div><button class="icon-button" type="button" aria-label="关闭饮食记录" :disabled="submitting" @click="close">×</button></header>

      <div class="dialog-content">
        <fieldset class="edit-fields" :disabled="locked">
          <legend class="sr-only">餐食信息与食物清单</legend>
          <div class="meal-meta">
            <label><span>餐次</span><select v-model="mealType"><option value="breakfast">早餐</option><option value="lunch">午餐</option><option value="dinner">晚餐</option><option value="custom">自定义</option></select></label>
            <label><span>时间</span><input v-model="recordedTime" type="time" required /></label>
            <label v-if="mealType === 'custom'" class="custom-meal-name"><span>餐次名称</span><input v-model="customMealName" maxlength="40" placeholder="例如：训练后加餐" required /></label>
          </div>

          <div class="editor-grid">
            <div class="add-food-column">
              <section class="search-box">
                <h3><span class="section-icon"><UiIcon name="meal" /></span>添加食物</h3>
                <form @submit.prevent="search"><input v-model="query" aria-label="搜索食物" placeholder="搜索米饭、鸡胸肉…" /><button type="submit" :disabled="searching || !query.trim()">{{ searching ? '搜索中' : '搜索' }}</button></form>
                <p v-if="searching" class="search-message" role="status">正在查找食物…</p>
                <p v-else-if="searchError" class="search-message" role="alert">{{ searchError }}</p>
                <p v-else-if="searched && !results.length" class="search-message" role="status">没有找到匹配食物，试试其他名称，或在下方自定义添加。</p>
                <p v-else-if="!searched" class="search-message">从常见食物中选择，加入后可调整数量和单位。</p>
                <div v-if="results.length" class="search-results">
                  <button v-for="result in results" :key="result.id" type="button" :disabled="items.length >= 20" :aria-label="`添加${result.name}`" @click="addTemplate(result)"><span><strong>{{ result.name }}</strong><small>{{ result.kcal_per_100g.low }}–{{ result.kcal_per_100g.high }} kcal / 100g</small></span><b aria-hidden="true">＋</b></button>
                </div>
              </section>

              <details class="custom-box qh-disclosure">
                <summary><strong>没有找到？自定义添加</strong><span>填写名称、份量与总热量</span></summary>
                <div class="custom-body">
                  <p class="custom-note">填写这项食物按当前份量的总热量；修改数量不会自动换算自填热量。</p>
                  <div class="custom-grid">
                    <label class="custom-food-name"><span>食物名称</span><input v-model="customName" maxlength="80" placeholder="食物名称" /></label>
                    <label><span>数量</span><input v-model.number="customQuantity" type="number" min="0.1" max="5000" step="0.1" aria-label="数量" /></label>
                    <label><span>单位</span><input v-model="customUnit" maxlength="20" aria-label="单位" /></label>
                    <label><span>总热量下限 · kcal</span><input v-model.number="customLow" type="number" min="0" max="20000" step="1" aria-label="热量下限" /></label>
                    <label><span>总热量上限 · kcal</span><input v-model.number="customHigh" type="number" min="0" max="20000" step="1" aria-label="热量上限" /></label>
                    <button type="button" :disabled="items.length >= 20" @click="addCustom">＋ 加入本餐</button>
                  </div>
                  <p v-if="customError" class="inline-error" role="alert">{{ customError }}</p>
                </div>
              </details>
              <p class="add-feedback" role="status">{{ feedback }}</p>
            </div>

            <section class="draft-list" aria-label="本餐清单">
              <div class="draft-heading"><h3>本餐清单</h3><span>{{ items.length }} / 20 项</span></div>
              <div v-if="!items.length" class="empty-draft"><span class="empty-icon"><UiIcon name="meal" /></span><strong>这一餐吃了什么？</strong><p>添加食物后，在这里核对份量。</p></div>
              <p v-else class="draft-hint">核对每项份量，再保存整餐。</p>
              <article v-for="item in items" :key="item.key">
                <div class="item-heading"><div><strong>{{ item.displayName }}</strong><small>{{ item.source }}</small></div><button class="remove-button" type="button" :aria-label="`删除${item.displayName}`" @click="removeItem(item)">移除</button></div>
                <div class="quantity-fields"><label><span>数量</span><input v-model.number="item.quantity" type="number" min="0.1" max="5000" step="0.1" :aria-label="`${item.displayName}数量`" /></label><label><span>单位</span><select v-model="item.unit" :aria-label="`${item.displayName}单位`"><option v-for="unit in item.units" :key="unit">{{ unit }}</option></select></label></div>
                <div v-if="item.kcal" class="item-energy"><label><span>总热量下限 · kcal</span><input v-model.number="item.kcal.low" type="number" min="0" max="20000" step="1" :aria-label="`${item.displayName}总热量下限`" /></label><label><span>总热量上限 · kcal</span><input v-model.number="item.kcal.high" type="number" min="0" max="20000" step="1" :aria-label="`${item.displayName}总热量上限`" /></label><p>按这项食物的总量填写，不会随数量自动换算。</p></div>
                <p v-else class="template-note">保存时按模板与所填份量计算热量。</p>
              </article>
              <p v-if="items.length >= 20" class="limit-note">本餐已达 20 项上限，可调整或移除已有食物。</p>
            </section>
          </div>
        </fieldset>
        <p v-if="draftError" class="form-error" role="alert">{{ draftError }}</p>
        <p v-if="localError" class="form-error" role="alert">{{ localError }}</p>
      </div>

      <footer class="dialog-footer">
        <div class="footer-summary" role="status"><strong>{{ submitting ? '正在保存这一餐…' : uncertain ? '保存状态待确认' : `${items.length} 项食物待保存` }}</strong><small>{{ uncertain ? '先核对今日记录，避免重复添加' : '保存后更新今日能量概览' }}</small></div>
        <div class="footer-actions"><button class="secondary-button" type="button" :disabled="submitting" @click="close">取消</button><button v-if="uncertain" type="button" class="primary-button" :disabled="store.busy" @click="checkRecords">查看今日餐食</button><button v-else class="primary-button" type="button" :disabled="!canSubmit || locked" @click="submit">{{ submitting ? '保存中…' : meal ? '保存修改' : '保存整餐' }}</button></div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: var(--qh-overlay); backdrop-filter: blur(4px); }
.dialog { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; width: min(840px, 100%); max-height: calc(100vh - 40px); max-height: calc(100dvh - 40px); overflow: hidden; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: 24px; background: var(--qh-cream); box-shadow: var(--qh-shadow); }
.dialog-header, .dialog-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px 24px; background: var(--qh-oat); }
.dialog-header { align-items: flex-start; border-bottom: 1px solid var(--qh-border); }
h2, h3, p { margin: 0; }
h2 { margin-top: 5px; font-size: 26px; letter-spacing: -.03em; line-height: 1.4; }
h3 { font-size: 17px; }
.eyebrow { color: var(--qh-muted); font-size: 12px; }
.header-copy { margin-top: 7px; color: var(--qh-muted); font-size: 13px; line-height: 1.7; }
.icon-button { flex: 0 0 40px; width: 40px; height: 40px; border: 0; border-radius: 50%; color: var(--qh-muted); background: var(--qh-cream); font-size: 25px; cursor: pointer; }
.dialog-content { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 20px 24px; scroll-padding-block: 20px; }
.edit-fields { min-width: 0; margin: 0; padding: 0; border: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.meal-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }
.custom-meal-name { grid-column: 1 / -1; }
label { display: grid; min-width: 0; gap: 6px; color: var(--qh-muted); font-size: 12px; font-weight: 500; }
input, select { width: 100%; min-width: 0; height: 44px; padding: 0 11px; border: 1px solid var(--qh-border); border-radius: 12px; color: var(--qh-berry); background: var(--qh-cream); font-size: 15px; }
input:hover, select:hover { border-color: var(--qh-berry); }
.editor-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; align-items: start; }
.add-food-column { min-width: 0; }
.search-box h3 { display: flex; align-items: center; gap: 8px; }
.section-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--qh-mint); }
.section-icon .ui-icon { width: 18px; height: 18px; }
.search-box form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; margin-top: 12px; }
.search-box form button, .custom-grid button { min-height: 44px; padding: 8px 16px; border: 0; border-radius: var(--qh-radius-pill); color: var(--qh-cream); background: var(--qh-berry); font-size: 13px; font-weight: 600; cursor: pointer; }
.search-message { margin-top: 10px; color: var(--qh-muted); font-size: 12px; line-height: 1.8; }
.search-results { display: grid; gap: 8px; max-height: 252px; overflow-y: auto; overscroll-behavior: contain; margin-top: 12px; padding: 3px; }
.search-results button { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 64px; padding: 12px; border: 1px solid var(--qh-border); border-radius: 14px; text-align: left; background: var(--qh-oat); cursor: pointer; }
.search-results button:hover:not(:disabled) { border-color: var(--qh-berry); }
.search-results span { display: grid; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.search-results strong { font-size: 14px; }
.search-results small { font-size: 11px; color: var(--qh-muted); }
.search-results b { display: grid; place-items: center; flex: 0 0 26px; width: 26px; height: 26px; border-radius: 50%; background: var(--qh-cream); font-size: 18px; font-weight: 400; }
.custom-box { margin-top: 18px; }
.custom-box > summary { display: grid; gap: 4px; padding: 15px 42px 15px 14px; }
.custom-box > summary strong { font-size: 13px; font-weight: 600; }
.custom-box > summary span { font-size: 11px; font-weight: 400; color: var(--qh-muted); }
.custom-box > summary::before, .custom-box > summary::after { right: 16px; }
.custom-body { padding: 14px; }
.custom-note { color: var(--qh-muted); font-size: 12px; line-height: 1.7; }
.custom-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 10px; margin-top: 12px; }
.custom-food-name, .custom-grid > button { grid-column: 1 / -1; }
.add-feedback { min-height: 20px; margin-top: 10px; font-size: 12px; color: var(--qh-muted); line-height: 1.7; }
.draft-list { border: 1px solid var(--qh-border-strong); border-radius: 20px; padding: 16px; min-width: 0; }
.draft-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.draft-heading > span { font-size: 12px; color: var(--qh-muted); }
.empty-draft { display: grid; justify-items: center; gap: 10px; padding: 32px 8px; text-align: center; }
.empty-icon { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; background: var(--qh-oat); }
.empty-icon .ui-icon { width: 23px; height: 23px; }
.empty-draft > strong { font-size: 14px; }
.empty-draft p, .draft-hint { color: var(--qh-muted); font-size: 12px; line-height: 1.7; }
.draft-hint { margin-top: 6px; }
.draft-list article { padding: 14px 0; border-bottom: 1px solid var(--qh-border); }
.draft-list article:last-of-type { border-bottom: 0; padding-bottom: 0; }
.item-heading { display: flex; align-items: start; justify-content: space-between; gap: 8px; }
.item-heading > div { display: grid; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.item-heading strong { font-size: 15px; }
.item-heading small { font-size: 11px; color: var(--qh-muted); line-height: 1.6; }
.remove-button { flex-shrink: 0; min-height: 44px; padding: 8px; border: 0; color: var(--qh-muted); background: transparent; font-size: 12px; cursor: pointer; }
.remove-button:hover:not(:disabled) { color: var(--qh-berry); }
.quantity-fields, .item-energy { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
.item-energy { padding: 10px; border-radius: 12px; background: var(--qh-oat); }
.item-energy p { grid-column: 1 / -1; color: var(--qh-muted); font-size: 11px; line-height: 1.7; }
.template-note { margin-top: 8px; color: var(--qh-muted); font-size: 11px; line-height: 1.7; }
.limit-note { margin-top: 14px; color: var(--qh-muted); font-size: 12px; }
.inline-error, .form-error { margin-top: 12px; color: var(--qh-berry); font-size: 12px; line-height: 1.8; }
.form-error { padding: 12px; border: 1px solid var(--qh-border); border-radius: 12px; background: var(--qh-oat); }
.dialog-footer { border-top: 1px solid var(--qh-border); padding-block: 16px; }
.footer-summary { display: grid; gap: 4px; }
.footer-summary strong { font-size: 13px; font-weight: 600; }
.footer-summary small { color: var(--qh-muted); font-size: 11px; }
.footer-actions { display: flex; gap: 10px; }
.primary-button, .secondary-button { min-height: 44px; padding: 10px 18px; border-radius: var(--qh-radius-pill); font-size: 14px; font-weight: 600; cursor: pointer; }
.primary-button { border: 1px solid var(--qh-berry); color: var(--qh-cream); background: var(--qh-berry); }
.secondary-button { border: 1px solid var(--qh-border); background: var(--qh-cream); }
button:disabled { opacity: .5; cursor: default; }
.edit-fields:disabled { opacity: .65; }
@media (max-width: 760px) {
  .modal-backdrop { align-items: end; padding: 0; }
  .dialog { width: 100%; max-height: 94vh; max-height: 94dvh; border-radius: 22px 22px 0 0; }
  .dialog-header, .dialog-content { padding: 16px; }
  .dialog-footer { padding: 12px 16px calc(12px + env(safe-area-inset-bottom)); }
  .icon-button { flex-basis: 44px; width: 44px; height: 44px; }
  h2 { font-size: 22px; }
  input, select { font-size: 16px; }
  .editor-grid { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .meal-meta { margin-bottom: 18px; }
  .search-results { max-height: 220px; }
  .empty-draft { padding: 22px 8px; }
}
@media (max-width: 420px) {
  .dialog-footer { flex-wrap: wrap; gap: 10px; }
  .footer-summary { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 8px; }
  .footer-actions { width: 100%; }
  .primary-button { flex: 1; }
}
</style>
