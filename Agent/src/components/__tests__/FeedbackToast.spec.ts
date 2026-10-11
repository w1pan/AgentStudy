import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import { useQinghengStore } from '@/stores/qingheng'
import FeedbackToast from '../FeedbackToast.vue'

it('dismisses successes automatically while retaining errors until explicit dismissal', async () => {
  vi.useFakeTimers()
  setActivePinia(createPinia())
  const store = useQinghengStore()
  const wrapper = mount(FeedbackToast)
  try {
    store.notifySuccess('已保存')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[role="status"]').text()).toContain('已保存')
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    store.error = '已保存，但刷新失败'
    store.notifySuccess('成功')
    await wrapper.vm.$nextTick()
    expect(store.notice).toBeNull()
    await vi.advanceTimersByTimeAsync(10000)
    expect(wrapper.get('[role="alert"]').text()).toContain('刷新失败')
    await wrapper.get('button').trigger('click')
    expect(store.error).toBe('')
  } finally { wrapper.unmount(); vi.useRealTimers() }
})
