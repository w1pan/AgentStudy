import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type Meal } from '@/api/qingheng'
import { ApiError } from '@/api/client'
import PhotoMealDialog from '../PhotoMealDialog.vue'

const meal: Meal = {
  id: 'photo-1', meal_type: 'lunch', display_name: '午餐', custom_meal_name: null,
  entry_method: 'photo', recorded_date: '2026-10-11', recorded_time: '12:30:00',
  kcal: { low: 503, high: 729 }, estimate_confidence: 'medium', editable: false, deletable: true,
  items: [{ id: 'rice', name: '米饭', template_id: null, category: '主食', quantity: 1, unit: '碗',
    grams: { low: 150, high: 200 }, kcal: { low: 200, high: 260 }, estimate_source: 'ai',
    estimate_confidence: 'medium', portion_basis: 'container', portion_detail: '一碗米饭',
    portion_confidence: 'medium', density_confidence: 'medium', source_name: '照片估算', source_version: 'v1' }],
}
const createUrl = vi.fn(() => 'blob:meal-preview')
const revokeUrl = vi.fn()
async function select(wrapper: VueWrapper, file = new File(['photo'], 'lunch.jpg', { type: 'image/jpeg' })) {
  const input = wrapper.get<HTMLInputElement>('[aria-label="选择整餐照片"]')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })
  await input.trigger('change')
  return file
}

describe('photo meal dialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    createUrl.mockClear()
    revokeUrl.mockClear()
    vi.stubGlobal('URL', class extends URL {
      static createObjectURL = createUrl
      static revokeObjectURL = revokeUrl
    })
  })
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

  it('previews a chosen image, validates uploads and releases previews', async () => {
    const wrapper = mount(PhotoMealDialog)
    try {
      await select(wrapper, new File(['bad'], 'file.pdf', { type: 'application/pdf' }))
      expect(wrapper.get('[role="alert"]').text()).toContain('JPEG、PNG 或 WebP')
      expect(createUrl).not.toHaveBeenCalled()
      const tooLarge = new File(['image'], 'large.png', { type: 'image/png' })
      Object.defineProperty(tooLarge, 'size', { value: 10 * 1024 * 1024 + 1 })
      await select(wrapper, tooLarge)
      expect(wrapper.get('[role="alert"]').text()).toContain('10 MB')
      await select(wrapper)
      expect(wrapper.get('.preview-frame img').attributes('src')).toBe('blob:meal-preview')
      expect(wrapper.find('[role="alert"]').exists()).toBe(false)
      await select(wrapper, new File(['new'], 'new.png', { type: 'image/png' }))
      expect(revokeUrl).toHaveBeenCalledTimes(1)
      expect(wrapper.get('.preview-caption').text()).toContain('new.png')
      await wrapper.get('.preview-frame img').trigger('error')
      expect(wrapper.find('.photo-preview').exists()).toBe(false)
      expect(wrapper.get('.submit-photo').attributes('disabled')).toBeDefined()
      expect(revokeUrl).toHaveBeenCalledTimes(2)
      await select(wrapper)
    } finally { wrapper.unmount() }
    expect(revokeUrl).toHaveBeenCalledTimes(3)
  })

  it('locks submission and dismissal while saving, then shows saved food details', async () => {
    let finish!: (value: Meal) => void
    const create = vi.spyOn(api, 'createPhotoMeal').mockReturnValue(new Promise(resolve => { finish = resolve }))
    const wrapper = mount(PhotoMealDialog, { attachTo: document.body })
    try {
      const file = await select(wrapper)
      await wrapper.get('.submit-photo').trigger('click')
      await wrapper.get('.submit-photo').trigger('click')
      await wrapper.get('.close-button').trigger('click')
      await wrapper.get('.modal-backdrop').trigger('keydown', { key: 'Escape' })
      expect(create).toHaveBeenCalledExactlyOnceWith(file, 'lunch', null)
      expect(wrapper.emitted('close')).toBeUndefined()
      expect(wrapper.get('.meal-field').attributes('disabled')).toBeDefined()
      expect(wrapper.get('[role="status"]').text()).toContain('正在识别')
      finish(meal)
      await flushPromises()
      expect(wrapper.get('.result-banner').text()).toContain('午餐已入账')
      expect(wrapper.get('.food-list').text()).toContain('150–200 克')
      expect(wrapper.get<HTMLDetailsElement>('.meal-card').element.open).toBe(true)
      expect(wrapper.find('.meal-actions').exists()).toBe(false)
      expect(wrapper.find('.submit-photo').exists()).toBe(false)
      expect(document.activeElement).toBe(wrapper.get('.result-banner h3').element)
      await wrapper.get('.dialog-footer .primary').trigger('click')
      expect(wrapper.emitted('close')).toHaveLength(1)
    } finally { wrapper.unmount() }
  })

  it('retains photo and custom meal name for a retry after a confirmed failure', async () => {
    const create = vi.spyOn(api, 'createPhotoMeal').mockRejectedValueOnce(new ApiError('识别暂时不可用', 503)).mockResolvedValueOnce(meal)
    const wrapper = mount(PhotoMealDialog)
    try {
      const file = await select(wrapper)
      await wrapper.get('input[value="custom"]').setValue(true)
      expect(wrapper.get('.submit-photo').attributes('disabled')).toBeDefined()
      await wrapper.get('.name-input').setValue('  下午加餐  ')
      await wrapper.get('.submit-photo').trigger('click')
      await flushPromises()
      expect(wrapper.get('.form-error').text()).toContain('识别暂时不可用')
      expect(wrapper.get<HTMLInputElement>('.name-input').element.value).toBe('  下午加餐  ')
      expect(wrapper.find('.photo-preview').exists()).toBe(true)
      await wrapper.get('.submit-photo').trigger('click')
      await flushPromises()
      expect(create).toHaveBeenNthCalledWith(2, file, 'custom', '下午加餐')
      expect(wrapper.find('.result-banner').exists()).toBe(true)
    } finally { wrapper.unmount() }
  })

  it('asks to check records instead of offering a duplicate submission after a timeout', async () => {
    vi.spyOn(api, 'createPhotoMeal').mockRejectedValue(new ApiError('请求超时', 0))
    const wrapper = mount(PhotoMealDialog)
    try {
      await select(wrapper)
      await wrapper.get('.submit-photo').trigger('click')
      await flushPromises()
      expect(wrapper.get('.form-error').text()).toContain('无法确认是否已入账')
      expect(wrapper.find('.submit-photo').exists()).toBe(false)
      expect(wrapper.find('.manual-link').exists()).toBe(false)
      expect(wrapper.get('.dialog-footer .primary').text()).toBe('查看今日餐食')
      await wrapper.get('.dialog-footer .primary').trigger('click')
      await flushPromises()
      expect(wrapper.emitted('close')).toHaveLength(1)
    } finally { wrapper.unmount() }
  })
})
