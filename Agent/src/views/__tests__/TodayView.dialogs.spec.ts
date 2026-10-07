import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import { api, type DayDetail, type Meal } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'
import { currentRecordDate } from '@/utils/energy'
import TodayView from '../TodayView.vue'

afterEach(() => vi.restoreAllMocks())

function setup() {
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.profile = {
    age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 60,
    deficit_preset: 'gentle', bmi: 22, rmr_kcal: 1300,
    target_deficit: { low: 250, high: 350 }, updated_at: '',
  }
  const day: DayDetail = {
    summary: {
      record_date: currentRecordDate(), data_version: 1, rmr_kcal: 1300,
      intake: { low: 0, high: 0 }, baseline_expenditure: { low: 1560, high: 1560 },
      exercise_expenditure: { low: 0, high: 0 }, total_expenditure: { low: 1560, high: 1560 },
      deficit: { low: 1560, high: 1560 }, target_deficit: { low: 250, high: 350 }, risk_flags: [],
    },
    meals: [], exercises: [], weight: null,
  }
  store.today = day
  return { store, day }
}

it.each([false, true])('closes a saved meal dialog even if refresh fails: %s', async (refreshFails) => {
  const { store, day } = setup()
  let finish!: (day: DayDetail) => void
  let fail!: (error: Error) => void
  const save = vi.spyOn(api, 'createManualMeal').mockResolvedValue({} as Meal)
  vi.spyOn(api, 'getToday').mockImplementationOnce(() => new Promise((resolve, reject) => {
    finish = resolve
    fail = reject
  })).mockResolvedValue(day)
  const wrapper = mount(TodayView)
  try {
    await wrapper.get('.page-header .secondary-action').trigger('click')
    await wrapper.get('input[placeholder="食物名称"]').setValue('测试食物')
    await wrapper.get('.custom-grid button').trigger('click')
    await wrapper.get('.meal-dialog .primary-button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.meal-dialog').exists()).toBe(true)
    expect(wrapper.get('.draft-list').text()).toContain('测试食物')
    if (refreshFails) fail(new Error('临时断网'))
    else finish(day)
    await flushPromises()
    expect(wrapper.find('.meal-dialog').exists()).toBe(false)
    if (refreshFails) {
      expect(store.error).toContain('更改已保存')
      await wrapper.get('main .secondary-action').trigger('click')
      await flushPromises()
      expect(wrapper.find('.meal-dialog').exists()).toBe(false)
    }
    expect(save).toHaveBeenCalledOnce()
  } finally { wrapper.unmount() }
})

it('preserves an unsaved draft across a failed background refresh and retry', async () => {
  const { store, day } = setup()
  const wrapper = mount(TodayView)
  try {
    await wrapper.get('.page-header .secondary-action').trigger('click')
    await wrapper.get('input[placeholder="食物名称"]').setValue('未保存的食物')
    vi.spyOn(api, 'getToday').mockRejectedValueOnce(new Error('临时断网')).mockResolvedValueOnce(day)
    await store.reloadToday()
    await flushPromises()
    expect(wrapper.get('input[placeholder="食物名称"]').element).toHaveProperty('value', '未保存的食物')
    await store.reloadToday()
    await flushPromises()
    expect(wrapper.get('input[placeholder="食物名称"]').element).toHaveProperty('value', '未保存的食物')
  } finally { wrapper.unmount() }
})

it('contains keyboard focus and restores the trigger when Escape closes the dialog', async () => {
  setup()
  const wrapper = mount(TodayView, { attachTo: document.body })
  try {
    const trigger = wrapper.get<HTMLButtonElement>('.page-header .secondary-action')
    trigger.element.focus()
    await trigger.trigger('click')
    await flushPromises()
    const backdrop = wrapper.get('.modal-backdrop')
    const buttons = backdrop.findAll<HTMLButtonElement>('button:not(:disabled)')
    expect(backdrop.element.contains(document.activeElement)).toBe(true)
    const first = buttons[0]!
    first.element.focus()
    first.element.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true }))
    expect(document.activeElement).toBe(buttons[buttons.length - 1]!.element)
    buttons[buttons.length - 1]!.element.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }))
    expect(document.activeElement).toBe(first.element)
    await first.trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.meal-dialog').exists()).toBe(false)
    expect(document.activeElement).toBe(trigger.element)
  } finally { wrapper.unmount() }
})
