<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  api,
  type FoodTemplate,
  type ManualMealItemPayload,
  type Meal,
  type MealType,
} from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'

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
const customName = ref('')
const customQuantity = ref(1)
const customUnit = ref('份')
const customLow = ref(0)
const customHigh = ref(0)
const localError = ref('')

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

const canSubmit = computed(() => items.value.length > 0 && (mealType.value !== 'custom' || customMealName.value.trim()))

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  localError.value = ''
  try {
    results.value = await api.searchFoodTemplates(query.value.trim())
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '搜索失败'
  } finally {
    searching.value = false
  }
}

function addTemplate(template: FoodTemplate) {
  const units = Object.keys(template.units)
  const preferred = units.find((unit) => unit !== '克') || '克'
  items.value.push({
    key: crypto.randomUUID(),
    template_id: template.id,
    quantity: preferred === '克' ? 100 : 1,
    unit: preferred,
    displayName: template.name,
    units,
    source: `${template.source_name} · ${template.source_version}`,
  })
}

function addCustom() {
  localError.value = ''
  if (!customName.value.trim() || customLow.value < 0 || customHigh.value < customLow.value) {
    localError.value = '请填写有效的自定义名称和热量区间'
    return
  }
  items.value.push({
    key: crypto.randomUUID(),
    name: customName.value.trim(),
    quantity: customQuantity.value,
    unit: customUnit.value,
    kcal: { low: customLow.value, high: customHigh.value },
    displayName: customName.value.trim(),
    units: [customUnit.value],
    source: '用户填写 · 本次记录',
  })
  customName.value = ''
  customLow.value = 0
  customHigh.value = 0
}

async function submit() {
  if (!canSubmit.value) return
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
      kcal,
    })),
  }
  try {
    await store.mutate(() =>
      props.meal ? api.updateManualMeal(props.meal.id, payload) : api.createManualMeal(payload),
    )
    emit('close')
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '保存失败'
  }
}

onMounted(() => document.querySelector<HTMLInputElement>('.meal-dialog input')?.focus())
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="emit('close')">
    <section class="dialog meal-dialog" role="dialog" aria-modal="true" aria-label="手动记录饮食">
      <header><div><p class="eyebrow">手动记录</p><h2>{{ meal ? '编辑整餐' : '添加一餐' }}</h2></div><button class="icon-button" @click="emit('close')">×</button></header>

      <div class="meal-meta">
        <label><span>餐次</span><select v-model="mealType"><option value="breakfast">早餐</option><option value="lunch">午餐</option><option value="dinner">晚餐</option><option value="custom">自定义</option></select></label>
        <label v-if="mealType === 'custom'"><span>餐次名称</span><input v-model="customMealName" maxlength="40" placeholder="例如：训练后加餐" /></label>
        <label><span>时间</span><input v-model="recordedTime" type="time" /></label>
      </div>

      <section class="search-box">
        <h3>从内置模板添加</h3>
        <form @submit.prevent="search"><input v-model="query" placeholder="搜索米饭、鸡胸肉、番茄炒蛋…" /><button type="submit" :disabled="searching">搜索</button></form>
        <div v-if="results.length" class="search-results">
          <button v-for="result in results" :key="result.id" type="button" @click="addTemplate(result)">
            <span><strong>{{ result.name }}</strong><small>{{ result.kcal_per_100g.low }}–{{ result.kcal_per_100g.high }} kcal/100g</small></span><b>＋</b>
          </button>
        </div>
      </section>

      <section class="custom-box">
        <h3>或添加一次性食物</h3>
        <div class="custom-grid">
          <input v-model="customName" placeholder="食物名称" />
          <input v-model.number="customQuantity" type="number" min="0.1" step="0.1" aria-label="数量" />
          <input v-model="customUnit" maxlength="20" aria-label="单位" />
          <input v-model.number="customLow" type="number" min="0" aria-label="热量下限" placeholder="下限" />
          <input v-model.number="customHigh" type="number" min="0" aria-label="热量上限" placeholder="上限" />
          <button type="button" @click="addCustom">添加</button>
        </div>
      </section>

      <section class="draft-list">
        <h3>本餐组成 <small>{{ items.length }} 项</small></h3>
        <p v-if="!items.length" class="empty-copy">先搜索模板或添加一次性食物。</p>
        <article v-for="item in items" :key="item.key">
          <div><strong>{{ item.displayName }}</strong><small>{{ item.source }}</small></div>
          <input v-model.number="item.quantity" type="number" min="0.1" step="0.1" aria-label="数量" />
          <select v-if="item.units.length > 1" v-model="item.unit"><option v-for="unit in item.units" :key="unit">{{ unit }}</option></select>
          <span v-else>{{ item.unit }}</span>
          <button class="remove-button" type="button" @click="items = items.filter((entry) => entry.key !== item.key)">删除</button>
        </article>
      </section>

      <p v-if="localError" class="form-error">{{ localError }}</p>
      <footer><button class="secondary-button" @click="emit('close')">取消</button><button class="primary-button" :disabled="!canSubmit || store.busy" @click="submit">{{ meal ? '保存修改' : '保存整餐' }}</button></footer>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 40; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(33 38 30 / 38%); backdrop-filter: blur(4px); }
.dialog { width: min(760px, 100%); max-height: calc(100vh - 40px); overflow: auto; border: 1px solid var(--qh-border); border-radius: 24px; background: var(--qh-card); box-shadow: 0 28px 80px rgb(30 45 26 / 22%); }
header, footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 22px 24px; }
header { position: sticky; z-index: 2; top: 0; border-bottom: 1px solid var(--qh-border); background: rgb(255 254 249 / 94%); backdrop-filter: blur(12px); }
h2, h3, p { margin: 0; } h2 { margin-top: 3px; font-size: 24px; } h3 { font-size: 14px; }
.eyebrow { color: var(--qh-green-dark); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.icon-button { width: 38px; height: 38px; border: 0; border-radius: 12px; color: var(--qh-muted); background: var(--qh-sage-soft); font-size: 25px; cursor: pointer; }
.meal-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 20px 24px 0; }
label { display: grid; gap: 7px; color: var(--qh-muted); font-size: 12px; font-weight: 700; }
input, select { min-width: 0; height: 42px; padding: 0 11px; border: 1px solid var(--qh-border-strong); border-radius: 11px; color: var(--qh-text); background: white; }
.search-box, .custom-box, .draft-list { margin: 20px 24px 0; padding: 18px; border: 1px solid var(--qh-border); border-radius: 17px; }
.search-box form { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 12px; }
.search-box form button, .custom-grid button { padding: 0 16px; border: 0; border-radius: 11px; color: white; background: var(--qh-green); font-weight: 700; cursor: pointer; }
.search-results { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; max-height: 180px; margin-top: 10px; overflow: auto; }
.search-results button { display: flex; align-items: center; justify-content: space-between; padding: 11px; border: 1px solid var(--qh-border); border-radius: 11px; text-align: left; background: white; cursor: pointer; }
.search-results span { display: grid; gap: 3px; }.search-results small { color: var(--qh-muted); }.search-results b { color: var(--qh-green); font-size: 20px; }
.custom-grid { display: grid; grid-template-columns: 2fr .7fr .7fr 1fr 1fr auto; gap: 8px; margin-top: 12px; }
.draft-list h3 { display: flex; justify-content: space-between; }.draft-list h3 small { color: var(--qh-muted); }
.draft-list article { display: grid; grid-template-columns: minmax(140px, 1fr) 80px 65px auto; gap: 9px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--qh-border); }
.draft-list article:last-child { border-bottom: 0; }.draft-list article > div { display: grid; gap: 3px; }.draft-list article small, .empty-copy { color: var(--qh-muted); font-size: 11px; }
.remove-button { border: 0; color: #a24a3f; background: transparent; cursor: pointer; }
.form-error { margin: 14px 24px 0; padding: 10px 12px; border-radius: 10px; color: #8f3f35; background: #fff0ed; font-size: 13px; }
footer { position: sticky; bottom: 0; margin-top: 20px; border-top: 1px solid var(--qh-border); background: rgb(255 254 249 / 94%); }
.primary-button, .secondary-button { min-height: 43px; padding: 0 18px; border-radius: 12px; font-weight: 800; cursor: pointer; }.primary-button { border: 0; color: white; background: var(--qh-green); }.secondary-button { border: 1px solid var(--qh-border); background: white; }.primary-button:disabled { opacity: .5; cursor: not-allowed; }
@media (max-width: 640px) { .modal-backdrop { align-items: end; padding: 0; }.dialog { max-height: 94vh; border-radius: 22px 22px 0 0; }.meal-meta { grid-template-columns: 1fr 1fr; }.search-results { grid-template-columns: 1fr; }.custom-grid { grid-template-columns: 1fr 1fr 1fr; }.custom-grid input:first-child { grid-column: 1 / -1; }.draft-list article { grid-template-columns: 1fr 70px 50px; }.draft-list article .remove-button { grid-column: 1 / -1; justify-self: end; } }
</style>
