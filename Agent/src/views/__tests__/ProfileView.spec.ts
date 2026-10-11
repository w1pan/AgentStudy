import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useQinghengStore } from '@/stores/qingheng'

import ProfileView from '../ProfileView.vue'

describe('ProfileView', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.restoreAllMocks())

  it('shows required local-profile fields and formula disclosure', () => {
    const wrapper = mount(ProfileView, { props: { onboarding: true } })
    expect(wrapper.text()).toContain('先建立你的能量基线')
    expect(wrapper.text()).toContain('生理性别')
    expect(wrapper.text()).toContain('Mifflin–St Jeor')
    expect(wrapper.text()).toContain('18–64')
    expect(wrapper.find('.data-management').exists()).toBe(false)
    wrapper.unmount()
  })

  it('saves the selected target once and announces completion only after success', async () => {
    const store = useQinghengStore()
    let finish!: () => void
    const save = vi.spyOn(store, 'saveProfile').mockReturnValue(new Promise<void>(resolve => { finish = resolve }))
    const wrapper = mount(ProfileView)
    try {
      await wrapper.get('#profile-weight').setValue('65.2')
      await wrapper.get('input[value="standard"]').setValue(true)
      await wrapper.get('form').trigger('submit')
      await wrapper.get('form').trigger('submit')
      expect(save).toHaveBeenCalledExactlyOnceWith({ age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 65.2, deficit_preset: 'standard' })
      expect(wrapper.get('.form-fields').attributes('disabled')).toBeDefined()
      expect(wrapper.get('.save-feedback').text()).toBe('正在保存档案…')
      expect(wrapper.emitted('saved')).toBeUndefined()
      finish()
      await flushPromises()
      expect(wrapper.get('.save-feedback').text()).toBe('档案已保存')
      expect(wrapper.emitted('saved')).toHaveLength(1)
      await wrapper.get('#profile-age').setValue(31)
      expect(wrapper.get('.save-feedback').text()).not.toContain('档案已保存')
    } finally { wrapper.unmount() }
  })

  it('retains edits after a failed save and allows retry', async () => {
    const store = useQinghengStore()
    const save = vi.spyOn(store, 'saveProfile').mockRejectedValueOnce(new Error('保存失败')).mockResolvedValueOnce(undefined)
    const wrapper = mount(ProfileView)
    try {
      await wrapper.get('#profile-height').setValue('170.5')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(wrapper.get<HTMLInputElement>('#profile-height').element.value).toBe('170.5')
      expect(wrapper.get('.primary-button').attributes('disabled')).toBeUndefined()
      expect(wrapper.emitted('saved')).toBeUndefined()
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(save).toHaveBeenCalledTimes(2)
      expect(wrapper.emitted('saved')).toHaveLength(1)
    } finally { wrapper.unmount() }
  })

  it('shows saved estimates independently of an unsaved target change', async () => {
    const store = useQinghengStore()
    store.profile = { age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 60, deficit_preset: 'gentle', bmi: 22, rmr_kcal: 1300, target_deficit: { low: 250, high: 350 }, updated_at: '2026-10-11' }
    const wrapper = mount(ProfileView)
    try {
      await wrapper.get('input[value="standard"]').setValue(true)
      expect(wrapper.get('.target-note').text()).toContain('500–600')
      expect(wrapper.get('.profile-summary').text()).toContain('250–350')
      expect(wrapper.get('.profile-summary').text()).toContain('已保存的估算')
      expect(wrapper.get<HTMLDetailsElement>('.data-management').element.open).toBe(false)
    } finally { wrapper.unmount() }
  })

  it('clears history through the store only after the exact confirmation', async () => {
    const store = useQinghengStore()
    const clear = vi.spyOn(store, 'clearHistory').mockResolvedValue(undefined)
    const wrapper = mount(ProfileView)
    try {
      await wrapper.get('.danger-link').trigger('click')
      expect(clear).not.toHaveBeenCalled()
      await wrapper.get('.confirm-dialog input').setValue('清空')
      await wrapper.get('.confirm-dialog form').trigger('submit')
      expect(clear).not.toHaveBeenCalled()
      await wrapper.get('.confirm-dialog input').setValue('清空全部历史记录')
      await wrapper.get('.confirm-dialog form').trigger('submit')
      await flushPromises()
      expect(clear).toHaveBeenCalledOnce()
    } finally {
      wrapper.unmount()
      clear.mockRestore()
    }
  })
})
