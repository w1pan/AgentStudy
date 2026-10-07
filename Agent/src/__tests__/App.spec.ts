import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import App from '../App.vue'
import { useQinghengStore } from '@/stores/qingheng'
import type { DayDetail } from '@/api/qingheng'

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

it('refreshes at Shanghai midnight and removes the timer when unmounted', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-24T15:59:59Z'))
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.today = { summary: { record_date: '2026-09-24' } } as DayDetail
  vi.spyOn(store, 'initialize').mockImplementation(async () => { store.initialized = true })
  const reload = vi.spyOn(store, 'reloadToday').mockResolvedValue()
  const wrapper = shallowMount(App)
  await flushPromises()
  await vi.advanceTimersByTimeAsync(1000)
  expect(reload).toHaveBeenCalledOnce()
  store.today = { summary: { record_date: '2026-09-25' } } as DayDetail
  await vi.advanceTimersByTimeAsync(86_400_000)
  expect(reload).toHaveBeenCalledTimes(2)
  wrapper.unmount()
  await vi.advanceTimersByTimeAsync(86_400_000)
  expect(reload).toHaveBeenCalledTimes(2)
})

it('refreshes when returning to today or restoring visibility', async () => {
  setActivePinia(createPinia())
  const store = useQinghengStore()
  vi.spyOn(store, 'initialize').mockImplementation(async () => { store.initialized = true })
  const reload = vi.spyOn(store, 'reloadToday').mockResolvedValue()
  const wrapper = shallowMount(App)
  await flushPromises()
  window.history.replaceState(null, '', '#/records')
  window.dispatchEvent(new Event('hashchange'))
  window.history.replaceState(null, '', '#/today')
  window.dispatchEvent(new Event('hashchange'))
  expect(reload).toHaveBeenCalledOnce()
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  document.dispatchEvent(new Event('visibilitychange'))
  expect(reload).toHaveBeenCalledTimes(2)
  wrapper.unmount()
})

it('throttles focus refreshes and avoids repeating a visibility refresh', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-24T04:00:00Z'))
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.today = { summary: { record_date: '2026-09-24' } } as DayDetail
  vi.spyOn(store, 'initialize').mockImplementation(async () => { store.initialized = true })
  const reload = vi.spyOn(store, 'reloadToday').mockResolvedValue()
  const wrapper = shallowMount(App)
  await flushPromises()
  window.dispatchEvent(new Event('focus'))
  await vi.advanceTimersByTimeAsync(59_999)
  window.dispatchEvent(new Event('focus'))
  expect(reload).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(1)
  window.dispatchEvent(new Event('focus'))
  expect(reload).toHaveBeenCalledOnce()
  document.dispatchEvent(new Event('visibilitychange'))
  window.dispatchEvent(new Event('focus'))
  expect(reload).toHaveBeenCalledTimes(2)
  wrapper.unmount()
})

it('refreshes a stale day after a request spanning midnight finishes', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-24T15:59:59Z'))
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.today = { summary: { record_date: '2026-09-24' } } as DayDetail
  vi.spyOn(store, 'initialize').mockImplementation(async () => { store.initialized = true })
  const reload = vi.spyOn(store, 'reloadToday').mockResolvedValue()
  const wrapper = shallowMount(App)
  await flushPromises()
  store.busy = true
  await vi.advanceTimersByTimeAsync(1000)
  expect(reload).not.toHaveBeenCalled()
  store.busy = false
  await flushPromises()
  expect(reload).toHaveBeenCalledOnce()
  wrapper.unmount()
})

it.each([false, true])('does not loop when a midnight refresh returns an old date or fails: %s', async (fails) => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-24T15:59:59Z'))
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  setActivePinia(createPinia())
  const store = useQinghengStore()
  store.today = { summary: { record_date: '2026-09-23' } } as DayDetail
  vi.spyOn(store, 'initialize').mockImplementation(async () => { store.initialized = true })
  const reload = vi.spyOn(store, 'reloadToday').mockImplementation(async () => {
    store.busy = true
    await Promise.resolve()
    if (fails) store.today = null
    store.busy = false
  })
  const wrapper = shallowMount(App)
  try {
    await flushPromises()
    expect(reload).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()
    expect(reload).toHaveBeenCalledOnce()
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect(reload).toHaveBeenCalledOnce()
    // A later user action can still retry; it does not become a retry loop.
    await vi.advanceTimersByTimeAsync(60_000)
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect(reload).toHaveBeenCalledTimes(2)
  } finally { wrapper.unmount() }
})
