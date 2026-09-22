import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'

import { api } from '@/api/qingheng'
import { ApiError } from '@/api/client'
import { useQinghengStore } from '@/stores/qingheng'
import TodayView from '../TodayView.vue'
import ProfileView from '../ProfileView.vue'

it('reports advice failures and consumes the event-handler rejection', async () => {
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.today = {
    summary: {
      record_date: '2026-09-07', data_version: 1, rmr_kcal: 1300,
      intake: { low: 500, high: 600 }, baseline_expenditure: { low: 1560, high: 1560 },
      exercise_expenditure: { low: 0, high: 0 }, total_expenditure: { low: 1560, high: 1560 },
      deficit: { low: 960, high: 1060 }, target_deficit: { low: 250, high: 350 }, risk_flags: [],
    },
    meals: [], exercises: [], weight: null,
  }
  const message = '当前 AI 模型的免费额度已用完'
  const request = vi.spyOn(api, 'generateAdvice').mockRejectedValue(new ApiError(message, 503))
  const errorHandler = vi.fn()
  const wrapper = shallowMount(TodayView, { global: { config: { errorHandler } } })
  try {
    const button = wrapper.findAll('button').find((item) => item.text() === '生成今日建议')!
    await button.trigger('click')
    await flushPromises()
    expect(request).toHaveBeenCalledOnce()
    expect(store.error).toBe(message)
    expect(store.busy).toBe(false)
    expect(store.cachedAdvice).toBeNull()
    expect(errorHandler).not.toHaveBeenCalled()
    expect(button.attributes('disabled')).toBeUndefined()
  } finally {
    wrapper.unmount()
    request.mockRestore()
  }
})

it('keeps the saved weight when editing the profile after saving today weight', async () => {
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.profile = {
    age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 60,
    deficit_preset: 'gentle', bmi: 22, rmr_kcal: 1300,
    target_deficit: { low: 250, high: 350 }, updated_at: '2026-09-22T12:00:00+08:00',
  }
  const updated = { ...store.profile, current_weight_kg: 59, bmi: 21.7, rmr_kcal: 1290 }
  const day = {
    summary: {
      record_date: '2026-09-22', data_version: 2, rmr_kcal: 1290,
      intake: { low: 0, high: 0 }, baseline_expenditure: { low: 1548, high: 1548 },
      exercise_expenditure: { low: 0, high: 0 }, total_expenditure: { low: 1548, high: 1548 },
      deficit: { low: 1548, high: 1548 }, target_deficit: { low: 250, high: 350 }, risk_flags: [],
    },
    meals: [], exercises: [],
    weight: { recorded_date: '2026-09-22', weight_kg: 59, editable: true },
  }
  store.today = day
  const writeWeight = vi.spyOn(api, 'upsertWeight').mockResolvedValue(day.weight)
  vi.spyOn(api, 'getProfile').mockResolvedValue(updated)
  vi.spyOn(api, 'getToday').mockResolvedValue(day)
  const writeProfile = vi.spyOn(api, 'saveProfile').mockResolvedValue({ ...updated, age: 31 })
  const today = shallowMount(TodayView)
  let profileView: ReturnType<typeof shallowMount> | undefined
  try {
    await today.get('.weight-input input').setValue(59)
    await today.findAll('button').find((b) => b.text() === '保存今日体重')!.trigger('click')
    await flushPromises()
    expect(writeWeight).toHaveBeenCalledWith(59)
    expect(store.profile).toEqual(updated)
    today.unmount()
    profileView = shallowMount(ProfileView)
    expect(profileView.get('input[max="300"]').element).toHaveProperty('value', '59')
    await profileView.get('input[max="64"]').setValue(31)
    await profileView.get('form').trigger('submit')
    await flushPromises()
    expect(writeProfile).toHaveBeenCalledWith(expect.objectContaining({ age: 31, current_weight_kg: 59 }))
  } finally {
    if (!profileView) today.unmount()
    profileView?.unmount()
    vi.restoreAllMocks()
  }
})
