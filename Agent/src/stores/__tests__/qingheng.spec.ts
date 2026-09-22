import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type Profile } from '@/api/qingheng'
import { useQinghengStore } from '../qingheng'

const profile: Profile = {
  age: 30,
  biological_sex: 'female',
  height_cm: 165,
  current_weight_kg: 60,
  deficit_preset: 'gentle',
  bmi: 22,
  rmr_kcal: 1300,
  target_deficit: { low: 250, high: 350 },
  updated_at: '2026-08-19T12:00:00+08:00',
}

describe('qingheng store initialization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('preserves an existing profile when loading today fails', async () => {
    vi.spyOn(api, 'getProfile').mockResolvedValue(profile)
    vi.spyOn(api, 'getToday').mockRejectedValue(new Error('今日数据暂时不可用'))
    const store = useQinghengStore()

    await store.initialize()

    expect(store.profile).toEqual(profile)
    expect(store.hasProfile).toBe(true)
    expect(store.today).toBeNull()
    expect(store.error).toBe('今日数据暂时不可用')
    expect(store.initialized).toBe(true)
  })

  it('retains the committed weight if fetching the updated profile fails', async () => {
    const store = useQinghengStore()
    store.profile = { ...profile }
    vi.spyOn(api, 'upsertWeight').mockResolvedValue({
      recorded_date: '2026-09-22', weight_kg: 59, editable: true,
    })
    vi.spyOn(api, 'getProfile').mockRejectedValue(new Error('档案刷新失败'))

    await expect(store.saveWeight(59)).rejects.toThrow('档案刷新失败')

    expect(store.profile.current_weight_kg).toBe(59)
    expect(store.error).toBe('档案刷新失败')
    expect(store.busy).toBe(false)
  })

  it('keeps the old profile if the weight write fails', async () => {
    const store = useQinghengStore()
    store.profile = { ...profile }
    vi.spyOn(api, 'upsertWeight').mockRejectedValue(new Error('保存失败'))

    await expect(store.saveWeight(59)).rejects.toThrow('保存失败')

    expect(store.profile).toEqual(profile)
    expect(store.busy).toBe(false)
  })
})
