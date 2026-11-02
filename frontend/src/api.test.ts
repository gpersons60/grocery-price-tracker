import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  fetchComparison,
  fetchHistory,
  fetchProducts,
  fetchStores,
} from './api'

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

  it('returns an empty single-page history and encodes query parameters', async () => {
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
              store: { id: '271', name: 'Auchan', address: 'Boulevard Lobau' },
              period: '90d',
              observations: [],
              statistics: {
                latestPrice: null,
                minimumPrice: null,
                maximumPrice: null,
                meanPrice: null,
                observationCount: 0,
              },
            },
          }),
          { status: 200 },
        ),
      ),
    )

    await expect(fetchHistory('123', '271', '90d', 50)).resolves.toMatchObject({
      barcode: '123',
      observations: [],
    })
    const requestUrl = new URL(vi.mocked(fetch).mock.calls[0][0] as string)
    expect(requestUrl.pathname).toBe('/products/123/history')
    expect(requestUrl.searchParams.get('storeId')).toBe('271')
    expect(requestUrl.searchParams.get('period')).toBe('90d')
    expect(requestUrl.searchParams.get('pageSize')).toBe('50')
  })

  it('retrieves and combines every history page', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              data: {
                barcode: '123',
                store: {
                  id: '271',
                  name: 'Auchan',
                  address: 'Boulevard Lobau',
                },
                period: '90d',
                observations: [
                  {
                    store: {
                      id: '271',
                      name: 'Auchan',
                      address: 'Boulevard Lobau',
                    },
                    sourceObservationId: 'OPEN_PRICES#2',
                    observedDate: '2026-10-20',
                    price: '2.50',
                    currency: 'EUR',
                  },
                ],
                statistics: {
                  latestPrice: '2.50',
                  minimumPrice: '2.50',
                  maximumPrice: '2.50',
                  meanPrice: '2.50',
                  observationCount: 1,
                },
                continuationToken: 'next page',
              },
            }),
            { status: 200 },
          ),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              data: {
                barcode: '123',
                store: {
                  id: '271',
                  name: 'Auchan',
                  address: 'Boulevard Lobau',
                },
                period: '90d',
                observations: [
                  {
                    store: {
                      id: '271',
                      name: 'Auchan',
                      address: 'Boulevard Lobau',
                    },
                    sourceObservationId: 'OPEN_PRICES#1',
                    observedDate: '2026-10-10',
                    price: '1.20',
                    currency: 'EUR',
                    sourceUpdatedAt: '2026-10-21T10:00:00Z',
                  },
                ],
                statistics: {
                  latestPrice: '1.20',
                  minimumPrice: '1.20',
                  maximumPrice: '1.20',
                  meanPrice: '1.20',
                  observationCount: 1,
                },
              },
            }),
            { status: 200 },
          ),
        ),
    )

    const history = await fetchHistory('123', '271')

    expect(history.observations.map((item) => item.price)).toEqual([
      '2.50',
      '1.20',
    ])
    expect(history).not.toHaveProperty('statistics')
    expect(history.observations[1].sourceUpdatedAt).toBe(
      '2026-10-21T10:00:00Z',
    )
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2)
    const secondRequest = new URL(
      vi.mocked(fetch).mock.calls[1][0] as string,
    )
    expect(secondRequest.searchParams.get('continuationToken')).toBe(
      'next page',
    )
  })

  it('throws when a history page request fails', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { message: 'History is unavailable.' } }),
          { status: 503 },
        ),
      ),
    )

    await expect(fetchHistory('123', '271')).rejects.toThrow(
      'History is unavailable.',
    )
  })

  it('rejects repeated history continuation tokens', async () => {
    vi.stubEnv(
      'VITE_API_BASE_URL',
      'https://apgc1a8kvi.execute-api.us-east-2.amazonaws.com',
    )
    const page = {
      data: {
        barcode: '123',
        store: { id: '271', name: 'Auchan', address: 'Boulevard Lobau' },
        period: '90d',
        observations: [],
        statistics: {
          latestPrice: null,
          minimumPrice: null,
          maximumPrice: null,
          meanPrice: null,
          observationCount: 0,
        },
        continuationToken: 'repeat',
      },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() =>
        Promise.resolve(new Response(JSON.stringify(page), { status: 200 })),
      ),
    )

    await expect(fetchHistory('123', '271')).rejects.toThrow(
      'repeated continuation token',
    )
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2)
  })
})
