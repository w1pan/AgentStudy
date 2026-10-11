import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type Exercise, type MetActivity } from '@/api/qingheng'
import { ApiError } from '@/api/client'
import { useQinghengStore } from '@/stores/qingheng'
import ExerciseDialog from '../ExerciseDialog.vue'

const activities: MetActivity[] = [{ id: 'walk', name: '步行', mets: { low: 2, medium: 3, high: 4 }, source_version: 'test' }]
beforeEach(() => {
  setActivePinia(createPinia())
  useQinghengStore().profile = { age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 60, deficit_preset: 'gentle', bmi: 22, rmr_kcal: 1300, target_deficit: { low: 250, high: 350 }, updated_at: '' }
})
afterEach(() => vi.restoreAllMocks())

describe('exercise dialog', () => {
  it('retries loading and uses the corrected range in the preview and payload', async () => {
    vi.spyOn(api, 'getMetActivities').mockRejectedValueOnce(new Error('项目加载失败')).mockResolvedValueOnce(activities)
    vi.spyOn(api, 'getToday').mockRejectedValue(new Error('刷新失败'))
    const save = vi.spyOn(api, 'createExercise').mockResolvedValue({} as Exercise)
    const wrapper = mount(ExerciseDialog)
    try {
      await flushPromises()
      expect(wrapper.get('.load-state').text()).toContain('项目加载失败')
      expect(wrapper.get('footer .primary').attributes('disabled')).toBeDefined()
      await wrapper.get('.load-state button').trigger('click')
      await flushPromises()
      expect(wrapper.get('.estimate strong').text()).toBe('85–104')
      await wrapper.get('[aria-label="运动时长"]').setValue('')
      expect(wrapper.get('.estimate strong').text()).toBe('—')
      expect(wrapper.get('footer .primary').attributes('disabled')).toBeDefined()
      await wrapper.get('[aria-label="运动时长"]').setValue(45)
      await wrapper.get('.toggle input').setValue(true)
      await wrapper.get('[aria-label="运动热量下限"]').setValue(200)
      await wrapper.get('[aria-label="运动热量上限"]').setValue(100)
      expect(wrapper.get('footer .primary').attributes('disabled')).toBeDefined()
      await wrapper.get('[aria-label="运动热量上限"]').setValue(250)
      expect(wrapper.get('.estimate strong').text()).toBe('200–250')
      expect(wrapper.get('.estimate-label').text()).toBe('采用修正热量')
      await wrapper.get('footer .primary').trigger('click')
      await flushPromises()
      expect(save).toHaveBeenCalledWith(expect.objectContaining({ duration_minutes: 45, manual_kcal: { low: 200, high: 250 } }))
      expect(wrapper.emitted('close')).toHaveLength(1)
      expect(useQinghengStore().notice).toBeNull()
      expect(useQinghengStore().error).toContain('更改已保存')
    } finally { wrapper.unmount() }
  })

  it('prevents duplicate writes and dismissal, preserves values after a failed write', async () => {
    vi.spyOn(api, 'getMetActivities').mockResolvedValue(activities)
    let reject!: (error: Error) => void
    const save = vi.spyOn(api, 'createExercise').mockReturnValue(new Promise((_resolve, fail) => { reject = fail }))
    const wrapper = mount(ExerciseDialog)
    try {
      await flushPromises()
      await wrapper.get('[aria-label="运动时长"]').setValue(40)
      await wrapper.get('footer .primary').trigger('click')
      await wrapper.get('footer .primary').trigger('click')
      await wrapper.get('.modal-backdrop').trigger('keydown', { key: 'Escape' })
      expect(save).toHaveBeenCalledOnce()
      expect(wrapper.emitted('close')).toBeUndefined()
      reject(new ApiError('保存失败', 422))
      await flushPromises()
      expect(wrapper.get<HTMLInputElement>('[aria-label="运动时长"]').element.value).toBe('40')
      expect(wrapper.get('footer .primary').attributes('disabled')).toBeUndefined()
    } finally { wrapper.unmount() }
  })

  it('does not offer duplicate creation after an ambiguous timeout', async () => {
    vi.spyOn(api, 'getMetActivities').mockResolvedValue(activities)
    vi.spyOn(api, 'createExercise').mockRejectedValue(new ApiError('请求超时', 0))
    const wrapper = mount(ExerciseDialog)
    try {
      await flushPromises()
      await wrapper.get('footer .primary').trigger('click')
      await flushPromises()
      expect(wrapper.get('footer .primary').text()).toBe('查看今日活动')
      expect(wrapper.get('.form-error').text()).toContain('无法确认是否已保存')
    } finally { wrapper.unmount() }
  })
})
