import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import RangeMetric from '../RangeMetric.vue'

describe('RangeMetric', () => {
  it('renders an honest interval rather than a midpoint', () => {
    const wrapper = mount(RangeMetric, {
      props: { label: '今日摄入', value: { low: 1380, high: 1520 } },
    })
    expect(wrapper.text()).toContain('1380–1520')
    expect(wrapper.text()).not.toContain('1450 kcal')
  })
})
