import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { currentRecordDate } from '@/utils/energy'
import { api, type AdviceResponse, type DayDetail, type Profile, type ProfilePayload } from '@/api/qingheng'

export const useQinghengStore = defineStore('qingheng', () => {
  const profile = ref<Profile | null>(null)
  const today = ref<DayDetail | null>(null)
  const initialized = ref(false)
  const busy = ref(false)
  const error = ref('')
  const adviceCache = ref<Record<string, AdviceResponse>>({})
  let adviceGeneration = 0
  let todayRequest = 0

  const hasProfile = computed(() => profile.value !== null)
  const adviceKey = computed(() => {
    if (!today.value) return ''
    return `${today.value.summary.record_date}:${today.value.summary.data_version}`
  })
  const cachedAdvice = computed(() => adviceCache.value[adviceKey.value] || null)

  function setError(value: unknown) {
    error.value = value instanceof Error ? value.message : '操作失败'
  }

  async function initialize() {
    busy.value = true
    error.value = ''
    try {
      try {
        profile.value = await api.getProfile()
      } catch (value) {
        if (value instanceof ApiError && value.status === 404) {
          profile.value = null
          today.value = null
          return
        }
        throw value
      }

      try {
        today.value = await api.getToday()
      } catch (value) {
        today.value = null
        setError(value)
      }
    } catch (value) {
      setError(value)
      today.value = null
    } finally {
      initialized.value = true
      busy.value = false
    }
  }

  async function refreshToday() {
    if (!profile.value) return
    const request = ++todayRequest
    try {
      const result = await api.getToday()
      if (request === todayRequest) today.value = result
    } catch (value) {
      if (request !== todayRequest) return
      today.value = null
      throw value
    }
  }

  async function reloadToday() {
    if (busy.value || !profile.value) return
    busy.value = true
    error.value = ''
    if (today.value?.summary.record_date !== currentRecordDate()) today.value = null
    try {
      await refreshToday()
    } catch (value) {
      setError(value)
    } finally {
      busy.value = false
    }
  }

  async function saveProfile(payload: ProfilePayload) {
    await mutate(async () => { profile.value = await api.saveProfile(payload) })
  }

  async function mutate(action: () => Promise<unknown>, afterSave?: () => Promise<void>) {
    busy.value = true
    error.value = ''
    // Prevent a read started before this write from restoring an obsolete summary.
    todayRequest += 1
    try {
      await action()
      today.value = null
      try {
        await afterSave?.()
        await refreshToday()
      } catch {
        error.value = '更改已保存，但最新数据加载失败。请刷新今日数据，无需重复提交。'
      }
    } catch (value) {
      setError(value)
      throw value
    } finally {
      busy.value = false
    }
  }

  async function generateAdvice() {
    if (cachedAdvice.value) return cachedAdvice.value
    const generation = adviceGeneration
    busy.value = true
    error.value = ''
    try {
      const response = await api.generateAdvice()
      if (generation !== adviceGeneration) return null
      adviceCache.value[`${response.record_date}:${response.data_version}`] = response
      return response
    } catch (value) {
      setError(value)
      throw value
    } finally {
      busy.value = false
    }
  }

  async function clearHistory() {
    await mutate(async () => {
      await api.clearHistory()
      // Versions can be reused after deletion; invalidate before refreshing today.
      adviceGeneration += 1
      adviceCache.value = {}
      today.value = null
    })
  }

  async function saveWeight(weightKg: number) {
    await mutate(async () => {
      const saved = await api.upsertWeight(weightKg)
      // Preserve the committed weight even if a subsequent refresh fails.
      if (profile.value) {
        profile.value = { ...profile.value, current_weight_kg: saved.weight_kg }
      }
    }, async () => { profile.value = await api.getProfile() })
  }

  function clearError() {
    error.value = ''
  }

  return {
    profile,
    today,
    initialized,
    busy,
    error,
    hasProfile,
    cachedAdvice,
    initialize,
    refreshToday,
    reloadToday,
    saveProfile,
    saveWeight,
    clearHistory,
    mutate,
    generateAdvice,
    clearError,
  }
})
