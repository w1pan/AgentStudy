<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'

const props = defineProps<{ modelValue: string; max: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const root = ref<HTMLElement>()
const trigger = ref<HTMLButtonElement>()
const panel = ref<HTMLElement>()
const open = ref(false)
const year = ref(Number(props.modelValue.slice(0, 4)))
const id = useId()
const label = computed(() => `${Number(props.modelValue.slice(0, 4))}年${Number(props.modelValue.slice(5))}月`)
const valueFor = (month: number) => `${String(year.value).padStart(4, '0')}-${String(month).padStart(2, '0')}`
const isFuture = (month: number) => valueFor(month) > props.max

function close(restoreFocus = false) {
  open.value = false
  if (restoreFocus) trigger.value?.focus()
}
async function toggle() {
  if (open.value) return close()
  year.value = Number(props.modelValue.slice(0, 4))
  open.value = true
  await nextTick()
  panel.value?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus()
}
function select(value: string) {
  if (value > props.max) return
  emit('update:modelValue', value)
  close(true)
}
function outside(event: PointerEvent) {
  if (event.target instanceof Node && !root.value?.contains(event.target)) close()
}
function focusOut(event: FocusEvent) {
  if (!root.value?.contains(event.relatedTarget as Node | null)) close()
}
function navigate(event: KeyboardEvent) {
  const offsets: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 }
  const offset = offsets[event.key]
  if (offset === undefined) return
  const buttons = Array.from(panel.value?.querySelectorAll<HTMLButtonElement>('.month-option') || [])
  const index = buttons.indexOf(event.target as HTMLButtonElement)
  const target = buttons[index + offset]
  if (index < 0) return
  event.preventDefault()
  if (target && !target.disabled) target.focus()
}
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside))
</script>

<template>
  <div ref="root" class="month-picker" @focusout="focusOut" @keydown.esc.stop.prevent="close(true)">
    <span :id="`${id}-label`" class="picker-label">选择月份</span>
    <button ref="trigger" type="button" class="picker-trigger" :aria-expanded="open" :aria-controls="`${id}-panel`" :aria-label="`选择月份，当前${label}`" @click="toggle">
      <span>{{ label }}</span>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="4" y="5.5" width="16" height="15" rx="3" /><path d="M8 3v5m8-5v5M4 11h16m-11 4h3m2 0h3" /></svg>
    </button>
    <section v-if="open" :id="`${id}-panel`" ref="panel" class="picker-panel" :aria-labelledby="`${id}-label`" @keydown="navigate">
      <header class="year-controls">
        <button type="button" aria-label="上一年" :disabled="year <= 1" @click="year--">‹</button>
        <strong aria-live="polite">{{ year }} <small>年</small></strong>
        <button type="button" aria-label="下一年" :disabled="year >= Number(max.slice(0, 4))" @click="year++">›</button>
      </header>
      <div class="month-grid" role="group" aria-label="月份">
        <button v-for="month in 12" :key="month" type="button" class="month-option" :aria-label="`${year}年${month}月`" :aria-pressed="valueFor(month) === modelValue" :disabled="isFuture(month)" :class="{ selected: valueFor(month) === modelValue, current: valueFor(month) === max }" @click="select(valueFor(month))">{{ month }}月</button>
      </div>
      <footer><span>未来月份暂不可选</span><button type="button" class="current-month" @click="select(max)">回到本月</button></footer>
    </section>
  </div>
</template>

<style scoped>
.month-picker { position: relative; min-width: 0; display: grid; gap: 6px; }
.picker-label { color: var(--qh-muted); font-size: 12px; }
.picker-trigger { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 160px; min-height: 44px; padding: 9px 14px; border: 1px solid var(--qh-border-strong); border-radius: var(--qh-radius-control); background: var(--qh-cream); color: var(--qh-berry); cursor: pointer; font-family: var(--qh-numeral); font-weight: 600; font-size: 14px; }
.picker-trigger svg { width: 19px; height: 19px; flex-shrink: 0; }
.picker-trigger:hover, .picker-trigger[aria-expanded="true"] { background: var(--qh-oat); }
.picker-panel { position: absolute; top: calc(100% + 10px); right: 0; z-index: 20; width: min(292px, calc(100vw - 32px)); overflow: hidden; border: 1px solid var(--qh-berry); border-radius: 20px; background: var(--qh-cream); box-shadow: 0 5px 0 color-mix(in srgb, var(--qh-berry) 9%, transparent), 0 12px 30px rgb(48 45 41 / 10%); }
.year-controls { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: var(--qh-oat); border-bottom: 1px solid var(--qh-border); }
.year-controls strong { font-family: var(--qh-numeral); font-size: 19px; letter-spacing: .02em; }
.year-controls strong small { font-size: 12px; font-weight: 500; }
.year-controls button { width: 36px; min-height: 36px; border: 0; border-radius: 50%; background: transparent; color: var(--qh-berry); font-size: 23px; cursor: pointer; }
.year-controls button:not(:disabled):hover { background: var(--qh-cream); }
.month-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; padding: 14px; }
.month-option { position: relative; min-height: 44px; padding: 8px; border: 1px solid transparent; border-radius: 12px; color: var(--qh-berry); background: transparent; font-family: var(--qh-numeral); font-size: 14px; cursor: pointer; }
.month-option:not(:disabled):hover { background: var(--qh-oat); border-color: var(--qh-border); }
.month-option.current::after { position: absolute; content: ''; bottom: 4px; left: calc(50% - 2px); width: 4px; height: 4px; border-radius: 50%; background: currentColor; }
.month-option.selected, .month-option.selected:hover { background: var(--qh-berry); color: var(--qh-cream); font-weight: 700; }
button:disabled { opacity: .3; cursor: default; }
.picker-panel footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 14px; border-top: 1px solid var(--qh-border); }
footer > span { color: var(--qh-muted); font-size: 11px; }
.current-month { min-height: 36px; padding: 6px 10px; border: 0; border-radius: 10px; background: var(--qh-oat); color: var(--qh-berry); cursor: pointer; font-size: 12px; font-weight: 600; }
button:focus-visible { outline: 2px solid var(--qh-berry); outline-offset: 2px; }
@media (max-width: 760px) {
  .month-picker { flex: 1; }
  .picker-trigger { width: 100%; min-width: 0; }
  .picker-panel { left: 50%; right: auto; transform: translateX(-50%); }
  .year-controls button, .current-month { min-height: 44px; }
  .year-controls button { width: 44px; }
}
</style>
