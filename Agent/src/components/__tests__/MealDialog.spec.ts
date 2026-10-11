import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'

import { api, type FoodTemplate, type Meal } from '@/api/qingheng'
import MealDialog from '../MealDialog.vue'
import { ApiError } from '@/api/client'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it('validates custom totals and draft quantities without multiplying entered calories', async () => {
  setActivePinia(createPinia())
  const save = vi.spyOn(api, 'createManualMeal').mockResolvedValue({} as Meal)
  const wrapper = mount(MealDialog)
  try {
    await wrapper.get('.custom-box summary').trigger('click')
    await wrapper.get('input[placeholder="食物名称"]').setValue('酸奶')
    await wrapper.get('input[aria-label="数量"]').setValue(0)
    await wrapper.get('.custom-grid button').trigger('click')
    expect(wrapper.findAll('.draft-list article')).toHaveLength(0)
    expect(wrapper.get('.inline-error').text()).toContain('有效数量')
    await wrapper.get('input[aria-label="数量"]').setValue(2)
    await wrapper.get('input[aria-label="热量下限"]').setValue(100)
    await wrapper.get('input[aria-label="热量上限"]').setValue(90)
    await wrapper.get('.custom-grid button').trigger('click')
    expect(wrapper.findAll('.draft-list article')).toHaveLength(0)
    await wrapper.get('input[aria-label="热量上限"]').setValue(120)
    await wrapper.get('.custom-grid button').trigger('click')
    await wrapper.get('input[aria-label="酸奶数量"]').setValue('')
    expect(wrapper.get('.primary-button').attributes('disabled')).toBeDefined()
    await wrapper.get('input[aria-label="酸奶数量"]').setValue(3)
    await wrapper.get('input[aria-label="酸奶总热量上限"]').setValue(130)
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ items: [expect.objectContaining({ quantity: 3, kcal: { low: 100, high: 130 } })] }))
  } finally { wrapper.unmount() }
})

it('ignores stale food searches and distinguishes no results from a failed search', async () => {
  setActivePinia(createPinia())
  let finish!: (results: FoodTemplate[]) => void
  const search = vi.spyOn(api, 'searchFoodTemplates').mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    .mockResolvedValueOnce([]).mockRejectedValueOnce(new Error('暂时无法搜索'))
  const wrapper = mount(MealDialog)
  try {
    await wrapper.get('.search-box input').setValue('旧名称')
    await wrapper.get('.search-box form').trigger('submit')
    await wrapper.get('.search-box input').setValue('新名称')
    await wrapper.get('.search-box form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('.search-message').text()).toContain('没有找到匹配食物')
    finish([{ id: 'old', name: '旧食物' } as FoodTemplate])
    await flushPromises()
    expect(wrapper.find('.search-results').exists()).toBe(false)
    await wrapper.get('.search-box form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('.search-message').text()).toBe('暂时无法搜索')
    expect(search).toHaveBeenCalledTimes(3)
  } finally { wrapper.unmount() }
})

it('locks duplicate submissions and retains an editable draft after a confirmed failure', async () => {
  setActivePinia(createPinia())
  let reject!: (error: Error) => void
  const save = vi.spyOn(api, 'createManualMeal').mockReturnValueOnce(new Promise((_resolve, fail) => { reject = fail }))
    .mockResolvedValueOnce({} as Meal)
  const wrapper = mount(MealDialog)
  try {
    await wrapper.get('input[placeholder="食物名称"]').setValue('鸡蛋')
    await wrapper.get('.custom-grid button').trigger('click')
    await wrapper.get('.primary-button').trigger('click')
    await wrapper.get('.primary-button').trigger('click')
    await wrapper.get('.modal-backdrop').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('close')).toBeUndefined()
    expect(save).toHaveBeenCalledOnce()
    expect(wrapper.get('.edit-fields').attributes('disabled')).toBeDefined()
    reject(new ApiError('请核对食物信息', 422))
    await flushPromises()
    expect(wrapper.get('.draft-list').text()).toContain('鸡蛋')
    expect(wrapper.get('.edit-fields').attributes('disabled')).toBeUndefined()
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()
    expect(save).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('close')).toHaveLength(1)
  } finally { wrapper.unmount() }
})

it('offers record verification after an ambiguous create failure', async () => {
  setActivePinia(createPinia())
  const save = vi.spyOn(api, 'createManualMeal').mockRejectedValue(new ApiError('请求超时', 0))
  const wrapper = mount(MealDialog)
  try {
    await wrapper.get('input[placeholder="食物名称"]').setValue('鸡蛋')
    await wrapper.get('.custom-grid button').trigger('click')
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.primary-button').text()).toBe('查看今日餐食')
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()
    expect(save).toHaveBeenCalledOnce()
    expect(wrapper.emitted('close')).toHaveLength(1)
  } finally { wrapper.unmount() }
})

it('adds, removes and saves template and custom items without secure-context crypto', async () => {
  setActivePinia(createPinia())
  vi.stubGlobal('crypto', {})
  const template: FoodTemplate = {
    id: 'rice', name: '米饭', aliases: [], category: 'staple',
    kcal_estimate: 116, uncertainty_pct: 0.1,
    kcal_per_100g: { low: 104, high: 128 }, units: { 克: 1, 碗: 150 },
    source_name: '模板', source_version: 'test', source_url: null,
  }
  vi.spyOn(api, 'searchFoodTemplates').mockResolvedValue([template])
  const save = vi.spyOn(api, 'createManualMeal').mockResolvedValue({} as Meal)
  const wrapper = mount(MealDialog)
  try {
    await wrapper.get('.search-box input').setValue('米饭')
    await wrapper.get('.search-box form').trigger('submit')
    await flushPromises()
    await wrapper.get('.search-results button').trigger('click')
    await wrapper.get('input[placeholder="食物名称"]').setValue('自定义食物')
    await wrapper.get('input[aria-label="热量下限"]').setValue(80)
    await wrapper.get('input[aria-label="热量上限"]').setValue(100)
    await wrapper.get('.custom-grid button').trigger('click')
    expect(wrapper.findAll('.draft-list article')).toHaveLength(2)
    await wrapper.get('.draft-list article .remove-button').trigger('click')
    await wrapper.get('.search-results button').trigger('click')
    const rows = wrapper.findAll('.draft-list article')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('自定义食物')
    expect(rows[1]!.text()).toContain('米饭')
    await wrapper.get('.primary-button').trigger('click')
    await flushPromises()
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ items: [
      expect.objectContaining({ name: '自定义食物', kcal: { low: 80, high: 100 } }),
      expect.objectContaining({ template_id: 'rice', quantity: 1, unit: '碗' }),
    ] }))
    expect(wrapper.emitted('close')).toHaveLength(1)
  } finally {
    wrapper.unmount()
  }
})
