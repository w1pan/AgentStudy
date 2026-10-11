import { describe, expect, it, vi } from 'vitest'

import { client } from '../client'
import { api, streamAdviceFollowUp } from '../qingheng'

describe('qingheng advice API', () => {
  it('allows enough time for the advice model to finish', async () => {
    const response = {
      data: {
        record_date: '2026-08-18',
        data_version: 1,
        cards: [],
      },
    }
    const post = vi.spyOn(client, 'post').mockResolvedValue(response)

    await api.generateAdvice()

    expect(post).toHaveBeenCalledWith('/advice', undefined, { timeout: 120_000 })
    post.mockRestore()
  })
})

it.each([false, true])('only accepts a completed advice stream (completion marker: %s)', async (completed) => {
  const data = 'data: {"text":"回答"}\n\n' + (completed ? 'event: done\ndata: {}\n\n' : '')
  const fetchMock = vi.fn().mockResolvedValue(new Response(new ReadableStream({ start(controller) {
    controller.enqueue(new TextEncoder().encode(data))
    controller.close()
  } })))
  vi.stubGlobal('fetch', fetchMock)
  const onText = vi.fn()
  const controller = new AbortController()
  try {
    const request = streamAdviceFollowUp('next_meal', '问题', [], onText, controller.signal)
    if (completed) await expect(request).resolves.toBeUndefined()
    else await expect(request).rejects.toThrow('回答中断')
    expect(onText).toHaveBeenCalledWith('回答')
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/advice/follow-up', expect.objectContaining({ signal: controller.signal }))
  } finally { vi.unstubAllGlobals() }
})
