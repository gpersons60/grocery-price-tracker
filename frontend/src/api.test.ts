import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchProducts } from './api'

describe('fetchProducts', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns products from a successful response', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ data: [{ barcode: '123', name: 'Test product' }] }),
          { status: 200 },
        ),
      ),
    )

    await expect(fetchProducts()).resolves.toEqual([
      { barcode: '123', name: 'Test product' },
    ])
    expect(fetch).toHaveBeenCalledWith(
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com/products',
    )
  })

  it('throws the API error message for an unsuccessful response', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { message: 'Products service is unavailable.' },
          }),
          { status: 503 },
        ),
      ),
    )

    await expect(fetchProducts()).rejects.toThrow(
      'Products service is unavailable.',
    )
  })
})
