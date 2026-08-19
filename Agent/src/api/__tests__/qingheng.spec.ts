import { describe, expect, it, vi } from 'vitest'

import { client } from '../client'
import { api } from '../qingheng'

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
