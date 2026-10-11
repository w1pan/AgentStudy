import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { DailySummary } from '@/api/qingheng'
import { ENERGY_MAX, ENERGY_MIN, ENERGY_CENTER, energyArc, energyPoint } from '@/utils/energyArc'
import EnergyOverview from '../EnergyOverview.vue'

function summary(low = 500, high = 600): DailySummary {
  return {
    record_date: '2026-10-11', data_version: 1, rmr_kcal: 1900,
    intake: { low: 2350 - high, high: 2350 - low },
    baseline_expenditure: { low: 2350, high: 2350 },
    exercise_expenditure: { low: 0, high: 0 },
    total_expenditure: { low: 2350, high: 2350 },
    deficit: { low, high }, target_deficit: { low: 500, high: 600 }, risk_flags: [],
  }
}

describe('energy overview', () => {
  it('keeps expenditure visible without presenting an unrecorded day as a large deficit', () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(2350, 2350), hasMeals: false } })
    expect(wrapper.get('.energy-reading').text()).toContain('等待第一餐记录')
    expect(wrapper.find('.reading-value').exists()).toBe(false)
    expect(wrapper.find('.arc-estimate').exists()).toBe(false)
    expect(wrapper.find('.arc-point').exists()).toBe(false)
    expect(wrapper.find('.energy-overflow').exists()).toBe(false)
    expect(wrapper.find('.arc-overflow').exists()).toBe(false)
    expect(wrapper.get('.capsule-metric--expenditure').text()).toContain('2,350')
    wrapper.unmount()
  })

  it('updates the estimate and status from live props and emits the photo action', async () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(), hasMeals: true } })
    expect(wrapper.get('.reading-value').text()).toContain('500–600')
    expect(wrapper.get('.reading-status').text()).toBe('估算区间触及目标')
    await wrapper.setProps({ summary: summary(200, 300) })
    expect(wrapper.get('.reading-status').text()).toBe('缺口低于目标')
    await wrapper.get('.capture-button').trigger('click')
    expect(wrapper.emitted('capture')).toHaveLength(1)
    wrapper.unmount()
  })

  it('shows surplus as a positive magnitude while plotting the signed negative interval', () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(-400, -200), hasMeals: true } })
    expect(wrapper.get('.reading-label').text()).toBe('当前估算盈余')
    expect(wrapper.get('.reading-value').text()).toContain('200–400')
    expect(wrapper.get('.arc-estimate').attributes('d')).toBe(energyArc({ low: -400, high: -200 }))
    expect(wrapper.get('svg[role="img"]').attributes('aria-label')).toContain('盈余 200–400')
    wrapper.unmount()
  })

  it('preserves signs when the interval crosses zero', () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(-100, 100), hasMeals: true } })
    expect(wrapper.get('.reading-label').text()).toBe('当前能量平衡')
    expect(wrapper.get('.reading-value').text()).toContain('-100–100')
    expect(wrapper.get('.reading-status').text()).toContain('跨越')
    wrapper.unmount()
  })

  it.each([[1200, 1500], [-1000, -800]])('keeps off-scale values visible without drawing a fake interval: %i, %i', (low, high) => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(low, high), hasMeals: true } })
    expect(wrapper.find('.arc-estimate').exists()).toBe(false)
    expect(wrapper.get('.energy-overflow').text()).toContain(low > ENERGY_MAX ? '全部高于刻度上限' : '全部低于刻度下限')
    expect(wrapper.get('.arc-overflow').attributes('data-side')).toBe(low > ENERGY_MAX ? 'high' : 'low')
    expect(wrapper.get('.energy-legend').text()).toContain('当前估算（超出刻度）')
    expect(wrapper.get('svg[role="img"]').attributes('aria-label')).toContain('全部')
    expect(wrapper.text()).not.toContain('仅显示范围内的部分')
    expect(wrapper.get('.reading-value').text()).toContain(Math.abs(low).toLocaleString('zh-CN'))
    wrapper.unmount()
  })

  it.each([[900, 1200, ['high']], [-900, -400, ['low']], [-900, 1200, ['low', 'high']]])(
    'shows the visible portion and correct overflow directions for %i to %i', (low, high, sides) => {
      const wrapper = mount(EnergyOverview, { props: { summary: summary(low, high), hasMeals: true } })
      expect(wrapper.get('.arc-estimate').attributes('d')).toBe(energyArc({ low, high }))
      expect(wrapper.findAll('.arc-overflow').map(marker => marker.attributes('data-side'))).toEqual(sides)
      expect(wrapper.get('.energy-overflow').text()).toContain('仅显示范围内的部分')
      expect(wrapper.find('.legend-overflow').exists()).toBe(false)
      wrapper.unmount()
    },
  )

  it('clears overflow indicators when live data returns within the scale, including its exact endpoints', async () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(1621, 1847), hasMeals: true } })
    expect(wrapper.find('.arc-overflow').exists()).toBe(true)
    await wrapper.setProps({ summary: summary(ENERGY_MIN, ENERGY_MAX) })
    expect(wrapper.find('.arc-overflow').exists()).toBe(false)
    expect(wrapper.find('.energy-overflow').exists()).toBe(false)
    expect(wrapper.find('.legend-overflow').exists()).toBe(false)
    expect(wrapper.get('.energy-note').text()).toContain('随记录更新')
    wrapper.unmount()
  })

  it('marks a point estimate instead of inventing a nonzero uncertainty range', () => {
    const wrapper = mount(EnergyOverview, { props: { summary: summary(550, 550), hasMeals: true } })
    expect(wrapper.find('.arc-point').exists()).toBe(true)
    expect(wrapper.find('.arc-estimate').exists()).toBe(false)
    expect(wrapper.get('.reading-value').text()).toBe('550kcal')
    wrapper.unmount()
  })
})

describe('calibrated arc geometry', () => {
  it('places zero at 37.5% of the angular scale, not at the top of the arc', () => {
    const p = energyPoint(0)
    const angle = Math.atan2(p.y - ENERGY_CENTER.y, p.x - ENERGY_CENTER.x) * 180 / Math.PI
    expect((angle + 135) / 90).toBeCloseTo(0.375)
    expect(p.x).toBeLessThan(360)
    expect(energyPoint(ENERGY_MIN).y).toBeCloseTo(energyPoint(ENERGY_MAX).y)
  })

  it('uses a 90-degree arc with the original width and a lower rise', () => {
    const left = energyPoint(ENERGY_MIN)
    const right = energyPoint(ENERGY_MAX)
    const apex = energyPoint((ENERGY_MIN + ENERGY_MAX) / 2)
    const angle = (p: { x: number; y: number }) => Math.atan2(p.y - ENERGY_CENTER.y, p.x - ENERGY_CENTER.x) * 180 / Math.PI
    expect(angle(right) - angle(left)).toBeCloseTo(90)
    expect(right.x - left.x).toBeCloseTo(536.93575, 4)
    expect(apex.y).toBeCloseTo(50)
    expect(left.y - apex.y).toBeCloseTo(111.20304, 4)
  })

  it('clips partially visible intervals at the scale edges', () => {
    expect(energyArc({ low: -900, high: 1200 })).toBe(energyArc({ low: ENERGY_MIN, high: ENERGY_MAX }))
    expect(energyArc({ low: 900, high: 1200 })).toBe(energyArc({ low: 900, high: ENERGY_MAX }))
  })
})
