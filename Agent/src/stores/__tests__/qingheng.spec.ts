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
})
