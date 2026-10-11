<script setup lang="ts">
import { computed } from 'vue'
import type { DailySummary, KcalRange } from '@/api/qingheng'
import { touchesTarget } from '@/utils/energy'
import { ENERGY_MIN, ENERGY_MAX, ENERGY_RADIUS, energyAngle, energyArc, energyPoint } from '@/utils/energyArc'
import LeafMark from './LeafMark.vue'
import UiIcon from './UiIcon.vue'

const props = defineProps<{ summary: DailySummary; hasMeals: boolean }>()
defineEmits<{ capture: [] }>()
const format = (value: number) => value.toLocaleString('zh-CN')
const rangeText = (value: KcalRange) => value.low === value.high
  ? format(value.low) : `${format(value.low)}–${format(value.high)}`
const surplus = computed(() => props.summary.deficit.high < 0)
const crossesZero = computed(() => props.summary.deficit.low < 0 && props.summary.deficit.high >= 0)
const label = computed(() => surplus.value ? '当前估算盈余' : crossesZero.value ? '当前能量平衡' : '当前估算缺口')
const displayedRange = computed(() => surplus.value
  ? { low: -props.summary.deficit.high, high: -props.summary.deficit.low }
  : props.summary.deficit)
const onTarget = computed(() => props.hasMeals && touchesTarget(props.summary.deficit, props.summary.target_deficit))
const status = computed(() => {
  if (!props.hasMeals) return '等待记录'
  if (surplus.value) return '处于盈余区间'
  if (crossesZero.value) return '区间跨越能量平衡点'
  if (onTarget.value) return '估算区间触及目标'
  return props.summary.deficit.high < props.summary.target_deficit.low ? '缺口低于目标' : '缺口高于目标'
})
const track = energyArc({ low: ENERGY_MIN, high: ENERGY_MAX })!
const arcEnds = [
  { label: '盈余', point: energyPoint(ENERGY_MIN) },
  { label: '缺口', point: energyPoint(ENERGY_MAX) },
]
const estimate = computed(() => props.hasMeals ? energyArc(props.summary.deficit) : null)
const target = computed(() => energyArc(props.summary.target_deficit, ENERGY_RADIUS + 13))
const targetLabel = computed(() => energyPoint((props.summary.target_deficit.low + props.summary.target_deficit.high) / 2, ENERGY_RADIUS + 38))
const ticks = [ENERGY_MIN, 0, ENERGY_MAX].map(value => ({
  value, label: value === ENERGY_MIN ? '−600' : value === 0 ? '0' : '1,000',
  inner: energyPoint(value, ENERGY_RADIUS - 7),
  outer: energyPoint(value, ENERGY_RADIUS + 7),
  text: energyPoint(value, ENERGY_RADIUS + 25),
}))
const pointEstimate = computed(() => props.hasMeals && props.summary.deficit.low === props.summary.deficit.high
  && props.summary.deficit.low >= ENERGY_MIN && props.summary.deficit.high <= ENERGY_MAX)
const point = computed(() => ({
  inner: energyPoint(props.summary.deficit.low, ENERGY_RADIUS - 7),
  outer: energyPoint(props.summary.deficit.low, ENERGY_RADIUS + 7),
}))
const overflows = computed(() => {
  if (!props.hasMeals) return []
  const range = props.summary.deficit
  const notes: string[] = []
  if (range.low < ENERGY_MIN) notes.push(`下限 ${format(range.low)} kcal，低于刻度下限 −600`)
  if (range.high > ENERGY_MAX) notes.push(`上限 ${format(range.high)} kcal，超出刻度上限 1,000`)
  return notes
})
const fullyOutside = computed(() => props.hasMeals && (
  props.summary.deficit.low > ENERGY_MAX || props.summary.deficit.high < ENERGY_MIN
))
const overflowMarkers = computed(() => {
  if (!props.hasMeals) return []
  return [
    { side: 'low', visible: props.summary.deficit.low < ENERGY_MIN, value: ENERGY_MIN, angle: energyAngle(ENERGY_MIN) - 90 },
    { side: 'high', visible: props.summary.deficit.high > ENERGY_MAX, value: ENERGY_MAX, angle: energyAngle(ENERGY_MAX) + 90 },
  ].filter(marker => marker.visible).map(marker => {
    const edge = energyPoint(marker.value)
    const radians = marker.angle * Math.PI / 180
    return { side: marker.side, transform: `translate(${edge.x + 14 * Math.cos(radians)} ${edge.y + 14 * Math.sin(radians)}) rotate(${marker.angle})` }
  })
})
const overflowMessage = computed(() => {
  if (!overflows.value.length) return ''
  if (fullyOutside.value) return props.summary.deficit.low > ENERGY_MAX
    ? '当前估算全部高于刻度上限 1,000 kcal，见右端箭头。'
    : '当前估算全部低于刻度下限 −600 kcal，见左端箭头。'
  return `估算区间${overflowMarkers.value.length === 2 ? '超出两端刻度' : props.summary.deficit.low < ENERGY_MIN ? '低于刻度下限 −600 kcal' : '超出刻度上限 1,000 kcal'}，弧线仅显示范围内的部分。`
})
const description = computed(() => props.hasMeals
  ? `${label.value} ${rangeText(displayedRange.value)} 千卡。目标缺口 ${rangeText(props.summary.target_deficit)} 千卡。${status.value}。刻度从盈余 600 到缺口 1,000 千卡。${overflowMessage.value}${overflows.value.join('；')}`
  : `尚未记录饮食，暂不展示缺口。目标缺口 ${rangeText(props.summary.target_deficit)} 千卡。`)
</script>

<template>
  <section class="energy-overview" aria-label="今日能量平衡">
    <header class="energy-heading">
      <h2>今日能量平衡</h2>
      <details class="energy-help">
        <summary>估算说明 <span aria-hidden="true">ⓘ</span></summary>
        <p>缺口 = 全天预计消耗 − 已记录摄入。正数表示缺口，负数表示盈余。未记录的餐食会使缺口偏高，当前估算不代表全天最终结果。图表刻度为 −600 至 1,000 kcal，越界时用端点箭头表示，中央始终显示完整估算值。</p>
      </details>
    </header>

    <div class="energy-capsule">
      <div class="capsule-metric">
        <span class="metric-icon metric-icon--intake"><UiIcon name="meal" /></span>
        <div><span class="metric-label">已记录摄入</span><p><strong>{{ rangeText(summary.intake) }}</strong><small>kcal</small></p></div>
      </div>
      <div class="energy-medallion" aria-hidden="true"><LeafMark /></div>
      <div class="capsule-metric capsule-metric--expenditure">
        <span class="metric-icon metric-icon--expenditure"><UiIcon name="flame" /></span>
        <div><span class="metric-label">预计消耗</span><p><strong>{{ rangeText(summary.total_expenditure) }}</strong><small>kcal</small></p></div>
      </div>
    </div>

    <div class="energy-chart">
      <svg class="energy-arc" viewBox="0 0 720 230" role="img" :aria-label="description">
        <path class="arc-track" :d="track" />
        <path v-if="target" class="arc-target" :d="target" />
        <path v-if="estimate" class="arc-estimate" :d="estimate" />
        <line v-if="pointEstimate" class="arc-point" :x1="point.inner.x" :y1="point.inner.y" :x2="point.outer.x" :y2="point.outer.y" />
        <path v-for="marker in overflowMarkers" :key="marker.side" class="arc-overflow" :data-side="marker.side" :transform="marker.transform" d="M -8 -5 L 0 0 L -8 5" />
        <g v-for="tick in ticks" :key="tick.value" class="arc-tick">
          <line :x1="tick.inner.x" :y1="tick.inner.y" :x2="tick.outer.x" :y2="tick.outer.y" />
          <text :x="tick.text.x" :y="tick.text.y - 5" text-anchor="middle">{{ tick.label }}</text>
        </g>
        <text class="arc-target-label" :x="targetLabel.x" :y="targetLabel.y - 8" text-anchor="middle">目标 {{ rangeText(summary.target_deficit) }}</text>
        <text v-for="end in arcEnds" :key="end.label" class="arc-end-label" :x="end.point.x" :y="end.point.y + 36" text-anchor="middle">{{ end.label }}</text>
      </svg>
      <div class="energy-reading" :class="{ 'energy-reading--empty': !hasMeals }">
        <template v-if="hasMeals">
          <p class="reading-label">{{ label }}</p>
          <p class="reading-value"><strong>{{ rangeText(displayedRange) }}</strong><span>kcal</span></p>
          <span class="reading-status" :class="{ 'reading-status--target': onTarget }">{{ status }}</span>
        </template>
        <template v-else>
          <p class="reading-label">每一餐，都是今天的起点</p>
          <strong class="empty-title">等待第一餐记录</strong>
          <span class="reading-status">记录后展示能量区间</span>
        </template>
      </div>
    </div>

    <div class="energy-legend">
      <span v-if="hasMeals"><i :class="[fullyOutside ? 'legend-overflow' : 'legend-estimate', { 'legend-overflow--low': fullyOutside && summary.deficit.high < 0 }]" />当前估算{{ fullyOutside ? '（超出刻度）' : '' }}</span>
      <span><i class="legend-target" />目标缺口 {{ rangeText(summary.target_deficit) }} kcal</span>
    </div>
    <p class="energy-note" :class="{ 'energy-overflow': overflowMessage }">{{ overflowMessage || (hasMeals ? '按已记录餐食估算，随记录更新。' : '先记下一餐，再了解今天的能量平衡。') }}</p>
    <footer class="energy-actions">
      <button class="capture-button" @click="$emit('capture')"><UiIcon name="camera" />拍照记录</button>
      <span>拍下整餐，轻松记一笔。</span>
    </footer>
  </section>
</template>

<style scoped>
.energy-overview { min-width: 0; padding: 18px 24px; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-card); background: var(--qh-card); }
.energy-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
h2 { margin: 0; font-size: 21px; }
.energy-help { position: relative; flex-shrink: 0; font-size: 12px; color: var(--qh-muted); }
.energy-help summary { cursor: pointer; list-style: none; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-pill); padding: 4px 10px; }
.energy-help summary::-webkit-details-marker { display: none; }
.energy-help p { position: absolute; top: 100%; right: 0; z-index: 5; width: min(290px, 70vw); padding: 16px; margin-top: 8px; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-control); background: var(--qh-card); box-shadow: var(--qh-shadow); line-height: 1.7; }
.energy-capsule { position: relative; display: grid; grid-template-columns: 1fr 1fr; align-items: stretch; border: var(--qh-stroke) solid var(--qh-border-strong); border-radius: var(--qh-radius-pill); background: var(--qh-oat); }
.capsule-metric { display: flex; align-items: center; justify-content: center; gap: 14px; min-width: 0; padding: 12px 48px 12px 22px; }
.capsule-metric--expenditure { border-left: 1px solid var(--qh-border); padding: 12px 22px 12px 48px; }
.metric-icon { display: grid; place-items: center; flex: 0 0 44px; width: 44px; height: 44px; border-radius: 50%; }
.metric-icon--intake { background: var(--qh-pink); }
.metric-icon--expenditure { color: var(--qh-red); background: color-mix(in srgb, var(--qh-yellow) 60%, var(--qh-cream)); }
.metric-icon--expenditure .ui-icon { width: 28px; height: 28px; }
.metric-label { font-size: 13px; font-weight: 700; }
.capsule-metric p { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px; margin: 0; line-height: 1.25; }
.capsule-metric strong { font-family: var(--qh-numeral); font-size: clamp(22px, 2.5vw, 34px); letter-spacing: -.035em; overflow-wrap: anywhere; }
.capsule-metric small { font-size: 12px; }
.energy-medallion { position: absolute; z-index: 1; top: 50%; left: 50%; display: grid; place-items: center; width: 78px; height: 78px; border: 2px solid var(--qh-berry); border-radius: 50%; background: var(--qh-red); color: white; box-shadow: 0 5px 0 var(--qh-berry); transform: translate(-50%, -50%); }
.energy-medallion .leaf-mark { width: 46px; height: 37px; }
.energy-chart { position: relative; width: min(680px, 100%); margin: 6px auto 0; }
.energy-arc { display: block; width: 100%; overflow: visible; }
.arc-track, .arc-target, .arc-estimate { fill: none; stroke-linecap: butt; }
.arc-track { stroke: color-mix(in srgb, var(--qh-oat) 88%, var(--qh-berry)); stroke-width: 7; }
.arc-target { stroke: var(--qh-mint); stroke-width: 6; }
.arc-estimate { stroke: var(--qh-pink); stroke-width: 7; }
.arc-tick line { stroke: var(--qh-berry); stroke-width: 1.5; }
.arc-tick text, .arc-end-label { fill: var(--qh-berry); font-size: 14px; font-weight: 600; }
.arc-target-label { fill: var(--qh-green-ink); font-size: 13px; font-weight: 600; }
.arc-point { stroke: var(--qh-berry); stroke-width: 3; stroke-linecap: butt; }
.arc-overflow { fill: none; stroke: var(--qh-berry); stroke-width: 2.5; stroke-linecap: butt; stroke-linejoin: miter; }
.energy-reading { position: absolute; top: 40%; left: 15%; right: 15%; display: grid; justify-items: center; text-align: center; gap: 6px; }
.reading-label { margin: 0; font-size: 13px; font-weight: 600; }
.reading-value { display: flex; align-items: baseline; justify-content: center; flex-wrap: wrap; column-gap: 6px; margin: 0; line-height: 1.15; }
.reading-value strong { font-family: var(--qh-numeral); font-size: clamp(30px, 4vw, 48px); letter-spacing: -.04em; overflow-wrap: anywhere; }
.reading-value span { font-size: 13px; }
.reading-status { display: inline-block; padding: 4px 14px; border-radius: var(--qh-radius-pill); font-size: 12px; color: var(--qh-muted); background: var(--qh-oat); }
.reading-status--target { color: var(--qh-green-ink); background: var(--qh-mint); }
.empty-title { font-size: clamp(20px, 2.5vw, 28px); }
.energy-legend { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px 20px; color: var(--qh-muted); font-size: 13px; }
.energy-legend > span { display: inline-flex; align-items: center; gap: 7px; }
.energy-legend i { display: inline-block; width: 15px; height: 5px; }
.legend-estimate { background: var(--qh-pink); }
.legend-target { background: var(--qh-mint); }
.energy-legend .legend-overflow { width: 7px; height: 7px; margin-right: 4px; border-top: 2px solid var(--qh-berry); border-right: 2px solid var(--qh-berry); transform: rotate(45deg); }
.energy-legend .legend-overflow--low { transform: rotate(225deg); }
.energy-note { margin: 6px 0 0; text-align: center; font-size: 13px; color: var(--qh-muted); overflow-wrap: anywhere; }
.energy-overflow { color: var(--qh-berry); }
.energy-actions { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 12px; }
.capture-button { display: inline-flex; justify-content: center; align-items: center; gap: 10px; min-height: 46px; min-width: 230px; padding: 8px 28px; border: 1px solid var(--qh-berry); border-radius: var(--qh-radius-pill); color: var(--qh-on-brand); background: var(--qh-brand); box-shadow: 0 3px 0 var(--qh-accent); font-size: 17px; font-weight: 700; cursor: pointer; }
.capture-button:hover { background: var(--qh-brand-hover); }
.energy-actions > span { font-size: 12px; color: var(--qh-muted); }
@media (max-width: 1050px) {
  .metric-icon { display: none; }
  .energy-reading { position: static; margin-top: -4px; margin-bottom: 14px; }
}
@media (max-width: 760px) {
  .energy-overview { padding: 16px 14px 20px; }
  .energy-heading { margin-bottom: 14px; }
  h2 { font-size: 18px; }
  .energy-help summary { display: flex; align-items: center; gap: 4px; }
  .energy-capsule { margin-top: 24px; border-radius: 20px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .capsule-metric { padding: 16px 10px 12px; flex-direction: column; gap: 6px; text-align: center; }
  .capsule-metric > div { min-width: 0; max-width: 100%; }
  .capsule-metric p { justify-content: center; }
  .metric-icon { display: grid; flex: 0 0 28px; width: 28px; height: 28px; }
  .metric-icon .ui-icon { width: 20px; height: 20px; }
  .metric-icon--expenditure .ui-icon { width: 23px; height: 23px; }
  .energy-medallion { top: 0; width: 36px; height: 36px; box-shadow: 0 3px 0 var(--qh-berry); }
  .energy-medallion .leaf-mark { width: 24px; height: 20px; }
  .capsule-metric strong { font-size: clamp(18px, 4.5vw, 26px); }
  .metric-label { font-size: 12px; }
  .reading-value strong { font-size: clamp(30px, 8vw, 44px); }
  .energy-chart { margin-top: 8px; }
  .arc-tick text, .arc-end-label { font-size: 24px; }
  .arc-target-label { display: none; }
  .energy-actions { flex-direction: column; gap: 10px; }
  .capture-button { width: min(100%, 340px); min-width: 0; }
}
@media (max-width: 420px) {
  .capsule-metric strong { font-size: 18px; }
  .arc-tick text, .arc-end-label { font-size: 32px; }
}
</style>
