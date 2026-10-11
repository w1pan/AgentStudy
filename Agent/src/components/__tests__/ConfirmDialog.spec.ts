import { flushPromises, mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import ConfirmDialog from '../ConfirmDialog.vue'

it('requires exact text, locks pending actions and retains the dialog after a failure', async () => {
  let fail!: (error: Error) => void
  const action = vi.fn().mockImplementationOnce(() => new Promise((_resolve, reject) => { fail = reject })).mockResolvedValueOnce(undefined)
  const wrapper = mount(ConfirmDialog, { props: { title: '清空记录？', description: '删除后无法恢复', confirmLabel: '确认清空', confirmationText: '清空全部历史记录', action } })
  try {
    await wrapper.get('input').setValue('清空')
    await wrapper.get('form').trigger('submit')
    expect(action).not.toHaveBeenCalled()
    await wrapper.get('input').setValue('清空全部历史记录')
    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')
    await wrapper.get('.confirm-backdrop').trigger('keydown', { key: 'Escape' })
    expect(action).toHaveBeenCalledOnce()
    expect(wrapper.emitted('close')).toBeUndefined()
    fail(new Error('连接失败'))
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('连接失败')
    expect(wrapper.emitted('done')).toBeUndefined()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.emitted('done')).toHaveLength(1)
  } finally { wrapper.unmount() }
})
