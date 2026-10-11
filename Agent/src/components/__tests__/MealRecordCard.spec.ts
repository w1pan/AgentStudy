import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Meal } from '@/api/qingheng'
import MealRecordCard from '../MealRecordCard.vue'

function meal(): Meal {
  return {
    id: 'lunch-1', meal_type: 'lunch', custom_meal_name: null, display_name: '午餐',
    entry_method: 'manual', recorded_date: '2026-10-11', recorded_time: '12:30:00',
    kcal: { low: 503, high: 729 }, estimate_confidence: null, editable: true, deletable: true,
    items: [{
      id: 'food-1', template_id: null, name: '米饭', category: '主食', quantity: 1, unit: '碗',
      grams: { low: 150, high: 200 }, kcal: { low: 200, high: 200 }, estimate_source: 'ai',
      estimate_confidence: 'medium', portion_basis: 'container', portion_detail: '一碗米饭',
      portion_confidence: 'low', density_confidence: 'high', source_name: '照片估算', source_version: 'v1',
    }],
  }
}

describe('meal record card', () => {
  it('keeps history details readable while hiding all mutation actions', () => {
    const wrapper = mount(MealRecordCard, { props: { meal: meal(), readonly: true } })
    expect(wrapper.get('.food-list').text()).toContain('米饭')
    expect(wrapper.find('.meal-actions').exists()).toBe(false)
    wrapper.unmount()
  })
  it('summarizes a closed meal and preserves its expanded state when its data updates', async () => {
    const value = meal()
    const wrapper = mount(MealRecordCard, { props: { meal: value } })
    const disclosure = wrapper.get<HTMLDetailsElement>('details.meal-card')
    expect(disclosure.element.open).toBe(false)
    expect(wrapper.get('.meal-summary').text()).toContain('午餐12:30')
    expect(wrapper.get('.meal-summary').text()).toContain('503–729')
    expect(wrapper.get('.meal-preview').text()).toBe('米饭')
    disclosure.element.open = true
    await wrapper.setProps({ meal: { ...value, kcal: { low: 600, high: 600 } } })
    expect(disclosure.element.open).toBe(true)
    expect(wrapper.get('.meal-kcal').text()).toBe('600kcal')
    expect(wrapper.get('.food-list').text()).toContain('150–200 克')
    expect(wrapper.get('.food-kcal').text()).toBe('200 kcal')
    expect(wrapper.get('.meal-provenance').text()).toContain('照片估算 · v1')
    expect(wrapper.get('.meal-provenance').text()).toContain('按容器：一碗米饭')
    expect(wrapper.get('.meal-provenance').text()).toContain('份量置信度：低')
    wrapper.unmount()
  })

  it('emits the selected meal for edit and delete, and disables both while saving', async () => {
    const value = meal()
    const wrapper = mount(MealRecordCard, { props: { meal: value } })
    await wrapper.get('.meal-edit').trigger('click')
    await wrapper.get('.meal-delete').trigger('click')
    expect(wrapper.emitted('edit')).toEqual([[value]])
    expect(wrapper.emitted('remove')).toEqual([[value]])
    await wrapper.setProps({ busy: true })
    await wrapper.get('.meal-edit').trigger('click')
    await wrapper.get('.meal-delete').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('remove')).toHaveLength(1)
    wrapper.unmount()
  })

  it('respects photo and read-only permissions without promising automatic rerecording', async () => {
    const value: Meal = { ...meal(), entry_method: 'photo', editable: false }
    const wrapper = mount(MealRecordCard, { props: { meal: value } })
    expect(wrapper.find('.meal-edit').exists()).toBe(false)
    expect(wrapper.get('.meal-delete').text()).toBe('删除记录')
    expect(wrapper.get('.meal-note').text()).toContain('删除后重新记录')
    await wrapper.setProps({ meal: { ...value, deletable: false } })
    expect(wrapper.find('.meal-actions').exists()).toBe(false)
    wrapper.unmount()
  })
})
