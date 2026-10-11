import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import { api, type DayDetail, type Exercise, type Meal } from '@/api/qingheng'
import { useQinghengStore } from '@/stores/qingheng'
import { currentRecordDate } from '@/utils/energy'
import TodayView from '../TodayView.vue'
import MealDialog from '@/components/MealDialog.vue'
import PhotoMealDialog from '@/components/PhotoMealDialog.vue'
import ExerciseDialog from '@/components/ExerciseDialog.vue'

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

it('opens both recording methods from the compact empty state', async () => {
  setup()
  const wrapper = mount(TodayView, { global: { stubs: { MealDialog: true, PhotoMealDialog: true } } })
  try {
    await wrapper.get('.empty-state-actions button').trigger('click')
    expect(wrapper.findComponent(PhotoMealDialog).exists()).toBe(true)
    wrapper.getComponent(PhotoMealDialog).vm.$emit('close')
    await flushPromises()
    await wrapper.get('.empty-state__manual').trigger('click')
    expect(wrapper.getComponent(MealDialog).props('meal')).toBeNull()
  } finally { wrapper.unmount() }
})

it('switches from photo recording to a fresh manual meal', async () => {
  setup()
  const wrapper = mount(TodayView, { global: { stubs: { MealDialog: true, PhotoMealDialog: true } } })
  try {
    await wrapper.get('.empty-state-actions button').trigger('click')
    wrapper.getComponent(PhotoMealDialog).vm.$emit('manual')
    await flushPromises()
    expect(wrapper.findComponent(PhotoMealDialog).exists()).toBe(false)
    expect(wrapper.getComponent(MealDialog).props('meal')).toBeNull()
  } finally { wrapper.unmount() }
})

it('opens new activity records from the empty state and header, and edits the selected activity', async () => {
  const { store, day } = setup()
  const exercise: Exercise = {
    id: 'walk-1', activity_id: 'walk', activity_name: '步行', intensity: 'medium', duration_minutes: 30,
    recorded_date: day.summary.record_date, recorded_time: '18:30:00', kcal: { low: 120, high: 160 },
    estimate_source: 'met', editable: true, deletable: true,
  }
  const wrapper = mount(TodayView, { global: { stubs: { ExerciseDialog: true } } })
  try {
    await wrapper.get('.activity-empty button').trigger('click')
    expect(wrapper.getComponent(ExerciseDialog).props('exercise')).toBeNull()
    wrapper.getComponent(ExerciseDialog).vm.$emit('close')
    store.today = { ...day, exercises: [exercise] }
    await flushPromises()
    await wrapper.get('.exercise-edit').trigger('click')
    expect(wrapper.getComponent(ExerciseDialog).props('exercise')).toEqual(exercise)
    wrapper.getComponent(ExerciseDialog).vm.$emit('close')
    await flushPromises()
    await wrapper.get('.activity-add').trigger('click')
    expect(wrapper.getComponent(ExerciseDialog).props('exercise')).toBeNull()
  } finally { wrapper.unmount() }
})

it('keeps an activity after a cancelled or failed deletion and refreshes after successful deletion', async () => {
  const { store, day } = setup()
  const exercise: Exercise = {
    id: 'walk-1', activity_id: 'walk', activity_name: '步行', intensity: 'medium', duration_minutes: 30,
    recorded_date: day.summary.record_date, recorded_time: '18:30:00', kcal: { low: 120, high: 160 },
    estimate_source: 'met', editable: true, deletable: true,
  }
  store.today = { ...day, exercises: [exercise] }
  const remove = vi.spyOn(api, 'deleteExercise').mockRejectedValueOnce(new Error('删除失败')).mockResolvedValueOnce(undefined)
  vi.spyOn(api, 'getToday').mockResolvedValue(day)
  const errorHandler = vi.fn()
  const wrapper = mount(TodayView, { global: { config: { errorHandler } } })
  try {
    await wrapper.get('.exercise-delete').trigger('click')
    expect(remove).not.toHaveBeenCalled()
    await wrapper.get('.confirm-cancel').trigger('click')
    await wrapper.get('.exercise-delete').trigger('click')
    await wrapper.get('.confirm-dialog form').trigger('submit')
    await flushPromises()
    expect(remove).toHaveBeenCalledWith(exercise.id)
    expect(wrapper.find('.exercise-card').exists()).toBe(true)
    expect(store.error).toBe('删除失败')
    expect(errorHandler).not.toHaveBeenCalled()
    await wrapper.get('.confirm-dialog form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.exercise-card').exists()).toBe(false)
    expect(wrapper.find('.activity-empty').exists()).toBe(true)
  } finally { wrapper.unmount() }
})

it('routes card actions to the selected meal and keeps it visible when deletion fails', async () => {
  const { store, day } = setup()
  const meal: Meal = {
    id: 'selected-lunch', meal_type: 'lunch', custom_meal_name: null, display_name: '午餐',
    entry_method: 'manual', recorded_date: day.summary.record_date, recorded_time: '12:30:00',
    kcal: { low: 503, high: 729 }, estimate_confidence: null, editable: true, deletable: true, items: [],
  }
  store.today = { ...day, meals: [meal] }
  const remove = vi.spyOn(api, 'deleteMeal').mockRejectedValueOnce(new Error('删除失败，请重试')).mockResolvedValueOnce(undefined)
  vi.spyOn(api, 'getToday').mockResolvedValue(day)
  const errorHandler = vi.fn()
  const wrapper = mount(TodayView, { global: { stubs: { MealDialog: true, PhotoMealDialog: true }, config: { errorHandler } } })
  try {
    await wrapper.get('.meal-edit').trigger('click')
    expect(wrapper.getComponent(MealDialog).props('meal')).toEqual(meal)
    wrapper.getComponent(MealDialog).vm.$emit('close')
    await flushPromises()
    await wrapper.get('.meal-delete').trigger('click')
    expect(remove).not.toHaveBeenCalled()
    await wrapper.get('.confirm-cancel').trigger('click')
    await wrapper.get('.meal-delete').trigger('click')
    await wrapper.get('.confirm-dialog form').trigger('submit')
    await flushPromises()
    expect(remove).toHaveBeenCalledWith(meal.id)
    expect(store.error).toBe('删除失败，请重试')
    expect(wrapper.find('.meal-card').exists()).toBe(true)
    expect(errorHandler).not.toHaveBeenCalled()
    await wrapper.get('.confirm-dialog form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.meal-card').exists()).toBe(false)
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  } finally { wrapper.unmount() }
})

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
