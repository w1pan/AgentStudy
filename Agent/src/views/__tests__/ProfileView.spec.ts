import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

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
})
