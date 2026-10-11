<script setup lang="ts">
import { computed } from 'vue'
import type { KcalRange, Meal } from '@/api/qingheng'
import UiIcon from './UiIcon.vue'

const props = defineProps<{ meal: Meal; busy?: boolean; readonly?: boolean }>()
defineEmits<{ edit: [meal: Meal]; remove: [meal: Meal] }>()
const foodNames = computed(() => props.meal.items.map(item => item.name).join(' · '))
const recordLabel = computed(() => `${props.meal.display_name} ${props.meal.recorded_time.slice(0, 5)}`)
const formatRange = (range: KcalRange) => range.low === range.high
  ? range.low.toLocaleString('zh-CN')
  : `${range.low.toLocaleString('zh-CN')}–${range.high.toLocaleString('zh-CN')}`
const sourceLabel = (source: string) => source === 'template' ? '食物模板' : source === 'ai' ? 'AI 估算' : '手动填写'
const confidenceLabel = (confidence: string | null) => ({ high: '高', medium: '中', low: '低' })[confidence || ''] || ''
const portionLabel = (basis: string | null) => ({
  count: '按数量', container: '按容器', package: '按包装',
  geometry: '按形状', mixed: '按混合菜', visual: '按画面体积',
})[basis || ''] || '自动估算'
</script>

<template>
  <details class="qh-disclosure meal-card" :class="`meal-card--${meal.meal_type}`">
    <summary class="meal-summary">
      <span class="meal-icon"><UiIcon name="meal" /></span>
      <span class="meal-heading">
        <span class="meal-title"><strong>{{ meal.display_name }}</strong><time :datetime="meal.recorded_time">{{ meal.recorded_time.slice(0, 5) }}</time></span>
        <span class="meal-preview" :title="foodNames">{{ foodNames || '暂无食物明细' }}</span>
        <span class="meal-meta">{{ meal.items.length }} 项食物<span aria-hidden="true"> · </span>{{ meal.entry_method === 'photo' ? '拍照记录' : '手动记录' }}</span>
      </span>
      <span class="meal-kcal"><strong>{{ formatRange(meal.kcal) }}</strong><small>kcal</small></span>
    </summary>

    <div class="meal-body">
      <div class="food-list-heading"><h3>食物与份量</h3><span>估算热量</span></div>
      <ul class="food-list">
        <li v-for="item in meal.items" :key="item.id">
          <div class="food-description">
            <strong>{{ item.name }}</strong>
            <span>{{ item.grams ? `${formatRange(item.grams)} 克` : `${item.quantity} ${item.unit}` }}<span aria-hidden="true"> · </span>{{ sourceLabel(item.estimate_source) }}</span>
          </div>
          <span class="food-kcal"><b>{{ formatRange(item.kcal) }}</b> <small>kcal</small></span>
        </li>
      </ul>
      <p v-if="!meal.items.length" class="meal-note">这条记录暂无食物明细。</p>

      <details v-if="meal.items.length" class="meal-provenance">
        <summary>查看估算依据</summary>
        <p v-if="meal.estimate_confidence">整餐估算置信度：{{ confidenceLabel(meal.estimate_confidence) }}</p>
        <dl>
          <template v-for="item in meal.items" :key="item.id">
            <dt>{{ item.name }}</dt>
            <dd>{{ item.source_name || sourceLabel(item.estimate_source) }}<template v-if="item.source_version"> · {{ item.source_version }}</template></dd>
            <dd v-if="item.estimate_confidence">综合置信度：{{ confidenceLabel(item.estimate_confidence) }}</dd>
            <dd v-if="item.portion_detail">{{ portionLabel(item.portion_basis) }}：{{ item.portion_detail }}</dd>
            <dd v-if="item.portion_confidence">份量置信度：{{ confidenceLabel(item.portion_confidence) }}</dd>
            <dd v-if="item.density_confidence">热量密度置信度：{{ confidenceLabel(item.density_confidence) }}</dd>
          </template>
        </dl>
      </details>

      <footer v-if="!readonly && (meal.editable || meal.deletable)" class="meal-actions">
        <p v-if="meal.entry_method === 'photo' && !meal.editable" class="meal-note">需要调整？可删除后重新记录。</p>
        <div>
          <button v-if="meal.editable" class="meal-edit" :disabled="busy" :aria-label="`编辑${recordLabel}的食物与份量`" @click="$emit('edit', meal)">编辑食物与份量</button>
          <button v-if="meal.deletable" class="meal-delete" :disabled="busy" :aria-label="`删除${recordLabel}的记录`" @click="$emit('remove', meal)">删除记录</button>
        </div>
      </footer>
    </div>
  </details>
</template>

<style scoped>
.meal-card { min-width: 0; container-type: inline-size; }
.meal-card--new { outline: 2px solid var(--qh-brand-soft); outline-offset: 3px; }
.meal-card > .meal-summary { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 18px 48px 18px 18px; }
.meal-summary::before, .meal-summary::after { right: 18px; }
.meal-summary:focus-visible { outline-offset: -4px; }
.meal-summary:hover { background: color-mix(in srgb, var(--qh-oat) 94%, var(--qh-berry)); }
.meal-card[open] > .meal-summary { border-bottom: 1px solid var(--qh-border); }
.meal-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; background: var(--qh-pink); color: var(--qh-berry); }
.meal-card--breakfast .meal-icon { background: var(--qh-yellow); }
.meal-card--lunch .meal-icon { background: var(--qh-mint); }
.meal-card--dinner .meal-icon { background: var(--qh-blue); }
.meal-icon .ui-icon { width: 21px; height: 21px; }
.meal-heading { min-width: 0; display: grid; gap: 4px; }
.meal-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: 5px 10px; }
.meal-title strong { font-size: 18px; line-height: 1.35; overflow-wrap: anywhere; }
.meal-title time { font-family: var(--qh-numeral); font-size: 13px; font-weight: 500; color: var(--qh-muted); }
.meal-preview { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--qh-muted); font-size: 13px; font-weight: 400; }
.meal-meta { font-size: 12px; font-weight: 400; color: var(--qh-muted); }
.meal-kcal { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: baseline; gap: 2px 5px; max-width: 180px; font-family: var(--qh-numeral); }
.meal-kcal strong { font-size: 24px; letter-spacing: -.035em; overflow-wrap: anywhere; }
.meal-kcal small { font-size: 12px; font-weight: 500; }
.meal-body { padding: 16px 18px; }
.food-list-heading { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
.food-list-heading h3 { margin: 0; font-size: 13px; font-weight: 600; }
.food-list-heading > span { color: var(--qh-muted); font-size: 12px; }
.food-list { list-style: none; padding: 0; margin: 4px 0 0; }
.food-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: 12px; padding: 13px 0; border-bottom: 1px solid var(--qh-border); }
.food-list li:last-child { border-bottom: 0; }
.food-description { display: grid; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.food-description strong { font-size: 14px; font-weight: 600; }
.food-description > span { color: var(--qh-muted); font-size: 12px; }
.food-kcal { font-family: var(--qh-numeral); text-align: right; overflow-wrap: anywhere; }
.food-kcal b { font-size: 14px; font-weight: 600; }
.food-kcal small { font-size: 11px; color: var(--qh-muted); }
.meal-provenance { color: var(--qh-muted); font-size: 12px; }
.meal-provenance > summary { cursor: pointer; padding: 10px 0; width: fit-content; }
.meal-provenance dl { margin: 0; padding: 12px; border-radius: 10px; background: var(--qh-cream); overflow-wrap: anywhere; line-height: 1.65; }
.meal-provenance dt { color: var(--qh-text); font-weight: 600; margin-top: 10px; }
.meal-provenance dt:first-child { margin-top: 0; }
.meal-provenance dd { margin: 0; }
.meal-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 8px 12px; margin-top: 6px; padding-top: 12px; border-top: 1px solid var(--qh-border); }
.meal-actions > div { display: flex; flex-wrap: wrap; gap: 8px; }
.meal-note { color: var(--qh-muted); font-size: 12px; line-height: 1.6; margin: 0 auto 0 0; }
.meal-actions button { min-height: 40px; padding: 8px 14px; border-radius: var(--qh-radius-pill); border: 1px solid var(--qh-border-strong); cursor: pointer; font-size: 13px; }
.meal-edit { color: var(--qh-on-brand); background: var(--qh-brand); }
.meal-edit:not(:disabled):hover { background: var(--qh-brand-hover); }
.meal-delete { color: var(--qh-muted); background: transparent; }
.meal-delete:not(:disabled):hover { color: var(--qh-danger); background: var(--qh-brand-soft); }
.meal-actions button:disabled { cursor: wait; opacity: .55; }
@container (max-width: 480px) {
  .meal-card > .meal-summary { grid-template-columns: 32px minmax(0, 1fr); gap: 8px 10px; padding: 14px 40px 14px 14px; }
  .meal-icon { width: 32px; height: 32px; align-self: start; }
  .meal-title strong { font-size: 17px; }
  .meal-kcal { grid-column: 2; justify-content: flex-start; max-width: none; }
  .meal-kcal strong { font-size: 22px; }
  .meal-body { padding: 14px; }
  .food-list li { grid-template-columns: minmax(0, 1fr) minmax(75px, auto); gap: 8px; }
  .meal-actions { justify-content: flex-start; }
  .meal-actions button { min-height: 44px; }
}
</style>
