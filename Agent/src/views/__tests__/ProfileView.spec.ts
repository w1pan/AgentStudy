import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useQinghengStore } from '@/stores/qingheng'

import ProfileView from '../ProfileView.vue'

describe('ProfileView', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows required local-profile fields and formula disclosure', () => {
    const wrapper = mount(ProfileView, { props: { onboarding: true } })
    expect(wrapper.text()).toContain('先建立你的能量基线')
    expect(wrapper.text()).toContain('生理性别')
    expect(wrapper.text()).toContain('Mifflin–St Jeor')
    expect(wrapper.text()).toContain('18–64')
  })

  it('clears history through the store only after the exact confirmation', async () => {
    const store = useQinghengStore()
    const clear = vi.spyOn(store, 'clearHistory').mockResolvedValue(undefined)
    const prompt = vi.spyOn(window, 'prompt').mockReturnValueOnce(null).mockReturnValueOnce('清空全部历史记录')
    const wrapper = mount(ProfileView)
    try {
      await wrapper.get('.danger-link').trigger('click')
      expect(clear).not.toHaveBeenCalled()
      await wrapper.get('.danger-link').trigger('click')
      await flushPromises()
      expect(clear).toHaveBeenCalledOnce()
    } finally {
      wrapper.unmount()
      prompt.mockRestore()
      clear.mockRestore()
    }
  })
})
