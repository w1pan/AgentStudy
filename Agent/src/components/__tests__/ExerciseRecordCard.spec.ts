import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { Exercise } from '@/api/qingheng'
import ExerciseRecordCard from '../ExerciseRecordCard.vue'

const exercise: Exercise = {
  id: 'walk-1', activity_id: 'walk', activity_name: '步行', intensity: 'medium', duration_minutes: 30,
  recorded_date: '2026-10-11', recorded_time: '18:30:00', kcal: { low: 120, high: 160 },
  estimate_source: 'met', editable: true, deletable: true,
}

describe('exercise record card', () => {
  it('hides mutation actions in history even for an editable record', () => {
    const wrapper = mount(ExerciseRecordCard, { props: { exercise, readonly: true } })
    expect(wrapper.get('.exercise-facts').text()).toContain('MET 估算')
    expect(wrapper.find('.exercise-actions').exists()).toBe(false)
    wrapper.unmount()
  })
  it('keeps the headline readable and the details expanded when estimates update', async () => {
    const wrapper = mount(ExerciseRecordCard, { props: { exercise } })
    const disclosure = wrapper.get<HTMLDetailsElement>('details')
    expect(disclosure.element.open).toBe(false)
    expect(wrapper.get('.exercise-summary').text()).toContain('步行')
    expect(wrapper.get('.exercise-meta').text()).toContain('30 分钟')
    expect(wrapper.get('time').text()).toBe('18:30')
    expect(wrapper.get('.exercise-energy strong').text()).toBe('120–160')
    expect(wrapper.get('.exercise-facts').text()).toContain('中等')
    expect(wrapper.get('.exercise-facts').text()).toContain('MET 估算')
    disclosure.element.open = true
    await wrapper.setProps({ exercise: { ...exercise, estimate_source: 'manual_adjusted', kcal: { low: 150, high: 150 } } })
    expect(disclosure.element.open).toBe(true)
    expect(wrapper.get('.exercise-energy strong').text()).toBe('150')
    expect(wrapper.get('.exercise-facts').text()).toContain('手动修正')
    expect(wrapper.get('.exercise-note').text()).toContain('填写的修正热量区间')
    wrapper.unmount()
  })

  it('emits actions for the selected exercise and prevents duplicate actions while busy', async () => {
    const wrapper = mount(ExerciseRecordCard, { props: { exercise } })
    await wrapper.get('.exercise-edit').trigger('click')
    await wrapper.get('.exercise-delete').trigger('click')
    expect(wrapper.emitted('edit')).toEqual([[exercise]])
    expect(wrapper.emitted('remove')).toEqual([[exercise]])
    await wrapper.setProps({ busy: true })
    await wrapper.get('.exercise-edit').trigger('click')
    await wrapper.get('.exercise-delete').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('remove')).toHaveLength(1)
    wrapper.unmount()
  })

  it('honors edit and delete permissions independently', async () => {
    const wrapper = mount(ExerciseRecordCard, { props: { exercise: { ...exercise, editable: false } } })
    expect(wrapper.find('.exercise-edit').exists()).toBe(false)
    expect(wrapper.find('.exercise-delete').exists()).toBe(true)
    await wrapper.setProps({ exercise: { ...exercise, editable: false, deletable: false } })
    expect(wrapper.find('.exercise-actions').exists()).toBe(false)
    wrapper.unmount()
  })
})
