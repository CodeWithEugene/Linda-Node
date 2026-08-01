import { afterEach, describe, expect, it, vi } from 'vitest'

import { AI_ASSIST_TIMEOUT_MS, api } from './api'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('allows AI assists enough time for the server-side NVIDIA retry budget', async () => {
    const setTimeout = vi.fn(() => 1)
    const clearTimeout = vi.fn()
    const fetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ summary: 'grounded' }) }))
    vi.stubGlobal('window', { setTimeout, clearTimeout })
    vi.stubGlobal('fetch', fetch)

    await expect(api('/api/cases/case_1/assists/explainer', { timeoutMs: AI_ASSIST_TIMEOUT_MS })).resolves.toEqual({ summary: 'grounded' })

    expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), AI_ASSIST_TIMEOUT_MS)
    expect(fetch).toHaveBeenCalledWith('/api/cases/case_1/assists/explainer', expect.not.objectContaining({ timeoutMs: expect.anything() }))
  })
})
