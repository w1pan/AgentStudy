import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, type DayDetail } from '@/api/qingheng'
import RecordsView from '../RecordsView.vue'
import MonthPicker from '@/components/MonthPicker.vue'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function day(date: string, weight: number): DayDetail {
  return {
    summary: {
      record_date: date, data_version: 1, rmr_kcal: 1300,
      intake: { low: 0, high: 0 }, baseline_expenditure: { low: 1560, high: 1560 },
      exercise_expenditure: { low: 0, high: 0 }, total_expenditure: { low: 1560, high: 1560 },
      deficit: { low: 1560, high: 1560 }, target_deficit: { low: 250, high: 350 }, risk_flags: [],
    },
    meals: [], exercises: [], weight: { recorded_date: date, weight_kg: weight, editable: false },
  }
}

async function loadedView() {
  vi.spyOn(api, 'getHistoryMonth').mockResolvedValue({ month: '2026-09', dates: ['2026-09-01', '2026-09-02'] })
  const request = vi.spyOn(api, 'getHistoryDay').mockResolvedValue(day('2026-09-02', 60))
  const wrapper = shallowMount(RecordsView)
  await flushPromises()
  return { wrapper, request }
}

describe('history request ordering', () => {
  afterEach(() => vi.restoreAllMocks())

  it('does not present an unrecorded diet as a calorie deficit', async () => {
    const { wrapper } = await loadedView()
    try {
      expect(wrapper.get('.balance-metric').text()).toContain('记录饮食后可估算')
      expect(wrapper.get('.balance-metric').text()).not.toContain('1,560')
      expect(wrapper.get('.summary-metrics').text()).toContain('当天未记录饮食')
      expect(wrapper.get('.summary-metrics').text()).toContain('1,560')
    } finally { wrapper.unmount() }
  })

  it('navigates months and stops at the current month', async () => {
    const { wrapper } = await loadedView()
    try {
      const picker = wrapper.getComponent(MonthPicker)
      const currentMonth = picker.props('modelValue')
      await wrapper.get('[aria-label="上个月"]').trigger('click')
      await flushPromises()
      expect(picker.props('modelValue')).not.toBe(currentMonth)
      await wrapper.get('[aria-label="下个月"]').trigger('click')
      await flushPromises()
      expect(picker.props('modelValue')).toBe(currentMonth)
      expect(wrapper.get('[aria-label="下个月"]').attributes('disabled')).toBeDefined()
    } finally { wrapper.unmount() }
  })

  it('keeps the newest date detail when the earlier date finishes last', async () => {
    const { wrapper, request } = await loadedView()
    const first = deferred<DayDetail>()
    const second = deferred<DayDetail>()
    request.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    try {
      await wrapper.findAll('.date-list button')[0]!.trigger('click')
      expect(wrapper.find('.day-detail').exists()).toBe(false)
      expect(wrapper.find('[role="status"]').exists()).toBe(true)
      await wrapper.findAll('.date-list button')[1]!.trigger('click')
      second.resolve(day('2026-09-02', 59))
      await flushPromises()
      first.resolve(day('2026-09-01', 88))
      await flushPromises()
      expect(wrapper.get('.day-heading').text()).toContain('2026-09-02')
      expect(wrapper.get('.weight-history').text()).toContain('59')
      expect(wrapper.get('.weight-history').text()).not.toContain('88')
    } finally { wrapper.unmount() }
  })

  it('ignores an old error and does not finish the current loading state early', async () => {
    const { wrapper, request } = await loadedView()
    const first = deferred<DayDetail>()
    const second = deferred<DayDetail>()
    request.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    try {
      await wrapper.findAll('.date-list button')[0]!.trigger('click')
      await wrapper.findAll('.date-list button')[1]!.trigger('click')
      first.reject(new Error('旧请求失败'))
      await flushPromises()
      expect(wrapper.find('.form-error').exists()).toBe(false)
      expect(wrapper.find('[role="status"]').exists()).toBe(true)
      second.reject(new Error('当前请求失败'))
      await flushPromises()
      expect(wrapper.get('.form-error').text()).toBe('当前请求失败')
      expect(wrapper.find('.day-detail').exists()).toBe(false)
      expect(wrapper.find('[role="status"]').exists()).toBe(false)
    } finally { wrapper.unmount() }
  })

  it('ignores an obsolete month list and does not request its day', async () => {
    const { wrapper, request } = await loadedView()
    const older = deferred<{ month: string; dates: string[] }>()
    vi.mocked(api.getHistoryMonth).mockReturnValueOnce(older.promise)
      .mockResolvedValueOnce({ month: '2026-07', dates: ['2026-07-01'] })
    request.mockResolvedValue(day('2026-07-01', 58))
    try {
      wrapper.getComponent(MonthPicker).vm.$emit('update:modelValue', '2026-08')
      await wrapper.vm.$nextTick()
      expect(wrapper.findAll('.date-list button')).toHaveLength(0)
      expect(wrapper.find('.day-detail').exists()).toBe(false)
      wrapper.getComponent(MonthPicker).vm.$emit('update:modelValue', '2026-07')
      await flushPromises()
      older.resolve({ month: '2026-08', dates: ['2026-08-01'] })
      await flushPromises()
      expect(wrapper.get('.day-heading').text()).toContain('2026-07-01')
      expect(wrapper.get('.date-list').text()).not.toContain('2026-08-01')
      expect(request).not.toHaveBeenCalledWith('2026-08-01')
    } finally { wrapper.unmount() }
  })

  it('ignores the default day of a month after the user selects another day', async () => {
    const pending = deferred<DayDetail>()
    vi.spyOn(api, 'getHistoryMonth').mockResolvedValue({ month: '2026-09', dates: ['2026-09-01', '2026-09-02'] })
    vi.spyOn(api, 'getHistoryDay').mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce(day('2026-09-01', 57))
    const wrapper = shallowMount(RecordsView)
    try {
      await flushPromises()
      await wrapper.findAll('.date-list button')[0]!.trigger('click')
      await flushPromises()
      pending.resolve(day('2026-09-02', 89))
      await flushPromises()
      expect(wrapper.get('.day-heading').text()).toContain('2026-09-01')
      expect(wrapper.get('.weight-history').text()).toContain('57')
    } finally { wrapper.unmount() }
  })

  it('does not show an old day after switching to an empty month', async () => {
    const { wrapper, request } = await loadedView()
    const pending = deferred<DayDetail>()
    request.mockReturnValueOnce(pending.promise)
    vi.mocked(api.getHistoryMonth).mockResolvedValueOnce({ month: '2026-06', dates: [] })
    try {
      await wrapper.findAll('.date-list button')[0]!.trigger('click')
      wrapper.getComponent(MonthPicker).vm.$emit('update:modelValue', '2026-06')
      await flushPromises()
      pending.resolve(day('2026-09-01', 80))
      await flushPromises()
      expect(wrapper.find('.day-detail').exists()).toBe(false)
      expect(wrapper.text()).toContain('这个月还没有记录')
      expect(wrapper.text()).toContain('没有可查看的日期')
    } finally { wrapper.unmount() }
  })
})
