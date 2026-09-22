import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import { api, type AdviceResponse, type DayDetail } from '@/api/qingheng'
import { useQinghengStore } from '../qingheng'

function day(version: number): DayDetail {
  return {
    summary: {
      record_date: '2026-09-22', data_version: version, rmr_kcal: 1300,
      intake: { low: 0, high: 0 }, baseline_expenditure: { low: 1560, high: 1560 },
      exercise_expenditure: { low: 0, high: 0 }, total_expenditure: { low: 1560, high: 1560 },
      deficit: { low: 1560, high: 1560 }, target_deficit: { low: 250, high: 350 }, risk_flags: [],
    },
    meals: [], exercises: [], weight: null,
  }
}

function advice(version: number, body = '清空前的建议'): AdviceResponse {
  return {
    record_date: '2026-09-22', data_version: version,
    cards: [{ type: 'status', title: '今日状态', body, bullets: [] }],
  }
}

describe('advice cache after clearing history', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const store = useQinghengStore()
    store.profile = {
      age: 30, biological_sex: 'female', height_cm: 165, current_weight_kg: 60,
      deficit_preset: 'gentle', bmi: 22, rmr_kcal: 1300,
      target_deficit: { low: 250, high: 350 }, updated_at: '2026-09-22T12:00:00+08:00',
    }
    store.today = day(1)
    vi.spyOn(api, 'clearHistory').mockResolvedValue(undefined)
    vi.spyOn(api, 'getToday').mockResolvedValue(day(1))
  })
  afterEach(() => vi.restoreAllMocks())

  it('discards all previous versions when the same date and versions are reused', async () => {
    const store = useQinghengStore()
    const request = vi.spyOn(api, 'generateAdvice')
      .mockResolvedValueOnce(advice(1))
      .mockResolvedValueOnce(advice(2))
      .mockResolvedValueOnce(advice(2, '新记录的建议'))
    await store.generateAdvice()
    store.today = day(2)
    await store.generateAdvice()

    await store.clearHistory()

    expect(store.cachedAdvice).toBeNull()
    store.today = day(2)
    expect(store.cachedAdvice).toBeNull()
    await store.generateAdvice()
    expect(request).toHaveBeenCalledTimes(3)
    expect(store.cachedAdvice?.cards[0]?.body).toBe('新记录的建议')
  })

  it('invalidates advice even if refreshing today fails after successful deletion', async () => {
    const store = useQinghengStore()
    vi.spyOn(api, 'generateAdvice').mockResolvedValue(advice(1))
    await store.generateAdvice()
    vi.mocked(api.getToday).mockRejectedValueOnce(new Error('刷新失败'))

    await expect(store.clearHistory()).rejects.toThrow('刷新失败')

    expect(store.today).toBeNull()
    expect(store.busy).toBe(false)
    expect(store.error).toBe('刷新失败')
    await store.refreshToday()
    expect(store.cachedAdvice).toBeNull()
  })

  it('preserves existing data and advice if deletion fails', async () => {
    const store = useQinghengStore()
    vi.spyOn(api, 'generateAdvice').mockResolvedValue(advice(1))
    await store.generateAdvice()
    vi.mocked(api.clearHistory).mockRejectedValueOnce(new Error('清空失败'))

    await expect(store.clearHistory()).rejects.toThrow('清空失败')

    expect(store.cachedAdvice).toEqual(advice(1))
    expect(store.today).toEqual(day(1))
    expect(api.getToday).not.toHaveBeenCalled()
    expect(store.busy).toBe(false)
  })

  it('ignores an old in-flight response arriving after deletion and new advice', async () => {
    const store = useQinghengStore()
    let resolveOld!: (value: AdviceResponse) => void
    vi.spyOn(api, 'generateAdvice')
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce(advice(1, '清空后的建议'))
    const pending = store.generateAdvice()
    await store.clearHistory()
    await store.generateAdvice()

    resolveOld(advice(1))
    expect(await pending).toBeNull()
    expect(store.cachedAdvice?.cards[0]?.body).toBe('清空后的建议')
  })
})
