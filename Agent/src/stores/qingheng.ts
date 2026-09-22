import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import { api, type AdviceResponse, type DayDetail, type Profile, type ProfilePayload } from '@/api/qingheng'

export const useQinghengStore = defineStore('qingheng', () => {
  const profile = ref<Profile | null>(null)
  const today = ref<DayDetail | null>(null)
  const initialized = ref(false)
  const busy = ref(false)
  const error = ref('')
  const adviceCache = ref<Record<string, AdviceResponse>>({})
  let adviceGeneration = 0

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
    today.value = await api.getToday()
  }

  async function saveProfile(payload: ProfilePayload) {
    busy.value = true
    error.value = ''
    try {
      profile.value = await api.saveProfile(payload)
      await refreshToday()
    } catch (value) {
      setError(value)
      throw value
    } finally {
      busy.value = false
    }
  }

  async function mutate(action: () => Promise<unknown>) {
    busy.value = true
    error.value = ''
    try {
      await action()
      await refreshToday()
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
      profile.value = await api.getProfile()
    })
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
    saveProfile,
    saveWeight,
    clearHistory,
    mutate,
    generateAdvice,
    clearError,
  }
})
