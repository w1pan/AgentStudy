import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MonthPicker from '../MonthPicker.vue'

describe('month picker', () => {
  it('selects an available month, disables the future, and restores trigger focus', async () => {
    const wrapper = mount(MonthPicker, { attachTo: document.body, props: { modelValue: '2026-09', max: '2026-10' } })
    try {
      await wrapper.get('.picker-trigger').trigger('click')
      expect(document.activeElement).toBe(wrapper.get('[aria-label="2026年9月"]').element)
      expect(wrapper.get('[aria-label="2026年11月"]').attributes('disabled')).toBeDefined()
      await wrapper.get('[aria-label="2026年11月"]').trigger('click')
      expect(wrapper.emitted('update:modelValue')).toBeUndefined()
      await wrapper.get('[aria-label="2026年8月"]').trigger('click')
      expect(wrapper.emitted('update:modelValue')).toEqual([['2026-08']])
      expect(wrapper.find('.picker-panel').exists()).toBe(false)
      expect(document.activeElement).toBe(wrapper.get('.picker-trigger').element)
    } finally { wrapper.unmount() }
  })

  it('browses years without selecting a month and can return to this month', async () => {
    const wrapper = mount(MonthPicker, { props: { modelValue: '2026-09', max: '2026-10' } })
    try {
      await wrapper.get('.picker-trigger').trigger('click')
      await wrapper.get('[aria-label="上一年"]').trigger('click')
      expect(wrapper.get('.year-controls').text()).toContain('2025')
      expect(wrapper.emitted('update:modelValue')).toBeUndefined()
      await wrapper.get('.current-month').trigger('click')
      expect(wrapper.emitted('update:modelValue')).toEqual([['2026-10']])
    } finally { wrapper.unmount() }
  })

  it('supports arrow navigation, Escape and outside dismissal without changing selection', async () => {
    const wrapper = mount(MonthPicker, { attachTo: document.body, props: { modelValue: '2026-09', max: '2026-10' } })
    try {
      await wrapper.get('.picker-trigger').trigger('click')
      await wrapper.get('[aria-label="2026年9月"]').trigger('keydown', { key: 'ArrowUp' })
      expect(document.activeElement).toBe(wrapper.get('[aria-label="2026年6月"]').element)
      await wrapper.get('.picker-panel').trigger('keydown', { key: 'Escape' })
      expect(wrapper.find('.picker-panel').exists()).toBe(false)
      expect(document.activeElement).toBe(wrapper.get('.picker-trigger').element)
      await wrapper.get('.picker-trigger').trigger('click')
      document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.picker-panel').exists()).toBe(false)
      expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    } finally { wrapper.unmount() }
  })
})
