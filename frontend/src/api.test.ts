import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchComparison, fetchProducts, fetchStores } from './api'

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

  it('returns stores from a successful response', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: [{ id: '271', name: 'Auchan', address: 'Boulevard Lobau' }],
          }),
          { status: 200 },
        ),
      ),
    )

    await expect(fetchStores()).resolves.toEqual([
      { id: '271', name: 'Auchan', address: 'Boulevard Lobau' },
    ])
    expect(fetch).toHaveBeenCalledWith(
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com/stores',
    )
  })

  it('returns comparison observations with decimal prices as strings', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
              barcode: '123',
              productName: 'Test product',
              stores: [
                {
                  store: {
                    id: '271',
                    name: 'Auchan',
                    address: 'Boulevard Lobau',
                  },
                  sourceObservationId: 'OPEN_PRICES#1',
                  observedDate: '2026-10-20',
                  price: '1.20',
                  currency: 'EUR',
                },
              ],
            },
          }),
          { status: 200 },
        ),
      ),
    )

    await expect(fetchComparison('123')).resolves.toEqual({
      barcode: '123',
      productName: 'Test product',
      stores: [
        {
          store: { id: '271', name: 'Auchan', address: 'Boulevard Lobau' },
          sourceObservationId: 'OPEN_PRICES#1',
          observedDate: '2026-10-20',
          price: '1.20',
          currency: 'EUR',
        },
      ],
    })
    expect(fetch).toHaveBeenCalledWith(
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com/products/123/comparison',
    )
  })

  it('throws the API error message for an unsuccessful comparison response', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { message: 'Product was not found.' } }),
          { status: 404 },
        ),
      ),
    )

    await expect(fetchComparison('123')).rejects.toThrow(
      'Product was not found.',
    )
  })
})
