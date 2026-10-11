import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import { streamAdviceFollowUp, type FollowUpMessage } from '@/api/qingheng'
import AdviceDrawer from '../AdviceDrawer.vue'

vi.mock('@/api/qingheng', () => ({ streamAdviceFollowUp: vi.fn().mockResolvedValue(undefined) }))

it('preserves IME confirmation and Shift+Enter, sending only on a normal Enter', async () => {
  const request = vi.mocked(streamAdviceFollowUp)
  request.mockClear()
  const wrapper = mount(AdviceDrawer, { props: {
    card: { type: 'next_meal', title: '下一餐', body: '按已记录的饮食安排。', bullets: [] },
    messages: [],
  } })
  try {
    const textarea = wrapper.get('textarea')
    await textarea.setValue('下一餐怎么搭配？')
    const composingEnter = new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, bubbles: true, cancelable: true })
    textarea.element.dispatchEvent(composingEnter)
    await flushPromises()
    expect(composingEnter.defaultPrevented).toBe(false)
    expect(request).not.toHaveBeenCalled()
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(request).not.toHaveBeenCalled()
    expect(wrapper.emitted('update:messages')).toBeUndefined()
    await textarea.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(request).toHaveBeenCalledExactlyOnceWith('next_meal', '下一餐怎么搭配？', [], expect.any(Function), expect.any(AbortSignal))
    expect(wrapper.get<HTMLTextAreaElement>('textarea').element.value).toBe('')
  } finally { wrapper.unmount() }
})

it('retries the failed question without duplicating its user message or partial answer', async () => {
  const request = vi.mocked(streamAdviceFollowUp).mockReset()
  request.mockImplementationOnce(async (_type, _message, _history, onText) => { onText('未完成'); throw new Error('连接中断') })
    .mockImplementationOnce(async (_type, _message, _history, onText) => { onText('完整回答') })
  let wrapper: VueWrapper
  wrapper = mount(AdviceDrawer, { props: {
    card: { type: 'next_meal', title: '下一餐', body: '建议', bullets: [] }, messages: [],
    'onUpdate:messages': (messages: FollowUpMessage[]) => { void wrapper.setProps({ messages }) },
  } })
  try {
    await wrapper.get('textarea').setValue('如何搭配？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('.message--assistant').text()).toBe('未完成')
    expect(wrapper.get('[role="alert"]').text()).toContain('连接中断')
    await wrapper.get('.retry-answer').trigger('click')
    await flushPromises()
    expect(request.mock.calls[1]?.[1]).toBe('如何搭配？')
    expect(request.mock.calls[1]?.[2]).toEqual([])
    expect(wrapper.findAll('.message--user')).toHaveLength(1)
    expect(wrapper.findAll('.message--assistant')).toHaveLength(1)
    expect(wrapper.get('.message--assistant').text()).toBe('完整回答')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  } finally { wrapper.unmount() }
})

it('keeps the reader position and supports stopping a streamed response', async () => {
  const request = vi.mocked(streamAdviceFollowUp).mockReset()
  let chunk!: (text: string) => void
  let signal!: AbortSignal
  request.mockImplementation((_type, _message, _history, onText, abortSignal) => new Promise((_resolve, reject) => {
    chunk = onText
    signal = abortSignal!
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }))
  let wrapper: VueWrapper
  wrapper = mount(AdviceDrawer, { props: {
    card: { type: 'next_meal', title: '下一餐', body: '建议', bullets: [] }, messages: [],
    'onUpdate:messages': (messages: FollowUpMessage[]) => { void wrapper.setProps({ messages }) },
  } })
  try {
    await wrapper.get('textarea').setValue('问题')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const area = wrapper.get<HTMLElement>('.conversation')
    Object.defineProperty(area.element, 'scrollHeight', { configurable: true, value: 1000 })
    Object.defineProperty(area.element, 'clientHeight', { configurable: true, value: 100 })
    area.element.scrollTop = 0
    await area.trigger('scroll')
    chunk('新增回答')
    await flushPromises()
    expect(area.element.scrollTop).toBe(0)
    expect(wrapper.find('.jump-latest').exists()).toBe(true)
    await wrapper.get('.jump-latest').trigger('click')
    expect(area.element.scrollTop).toBe(1000)
    await wrapper.get('.stop-answer').trigger('click')
    await flushPromises()
    expect(signal.aborted).toBe(true)
    expect(wrapper.get('[role="alert"]').text()).toContain('回答已停止')
    expect(wrapper.get('form button').text()).toBe('发送')
  } finally { wrapper.unmount() }
})
