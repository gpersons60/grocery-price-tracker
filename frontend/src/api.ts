export type Product = {
  barcode: string
  name: string
}

export type Store = {
  id: string
  name: string
  address: string
}

export type Observation = {
  store: Store
  sourceObservationId: string
  observedDate: string
  price: string
  currency: string
}

export type HistoryPeriod = '30d' | '90d' | '1y' | 'all'

export type HistoryObservation = Observation & {
  sourceUpdatedAt?: string
}

export type HistoryStatistics = {
  latestPrice: string | null
  minimumPrice: string | null
  maximumPrice: string | null
  meanPrice: string | null
  observationCount: number
}

export type History = {
  barcode: string
  store: Store
  period: HistoryPeriod
  observations: HistoryObservation[]
}

type HistoryPage = History & {
  statistics: HistoryStatistics
  continuationToken?: string
}

export type Comparison = {
  barcode: string
  productName: string
  stores: Observation[]
}

type ProductsResponse = {
  data: Product[]
}

type StoresResponse = {
  data: Store[]
}

type ComparisonResponse = {
  data: Comparison
}

type HistoryResponse = {
  data: HistoryPage
}

type ErrorResponse = {
  error?: {
    message?: string
  }
}

function getApiBaseUrl(): string {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '')
  if (!apiBaseUrl) {
    throw new Error(
      'The API base URL is not configured. Set VITE_API_BASE_URL in frontend/.env.local.',
    )
  }
  return apiBaseUrl
}

async function fetchJson<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`
  const response = signal ? await fetch(url, { signal }) : await fetch(url)
  if (!response.ok) {
    let message = `Unable to load data (HTTP ${response.status}).`
    try {
      const body = (await response.json()) as ErrorResponse
      if (body.error?.message) {
        message = body.error.message
      }
    } catch {}
    throw new Error(message)
  }

  return (await response.json()) as T
}

export async function fetchProducts(): Promise<Product[]> {
  const body = await fetchJson<ProductsResponse>('/products')
  return body.data
}

export async function fetchStores(): Promise<Store[]> {
  const body = await fetchJson<StoresResponse>('/stores')
  return body.data
}

export async function fetchComparison(barcode: string): Promise<Comparison> {
  const body = await fetchJson<ComparisonResponse>(
    `/products/${encodeURIComponent(barcode)}/comparison`,
  )
  return body.data
}

export async function fetchHistory(
  barcode: string,
  storeId: string,
  period: HistoryPeriod = '90d',
  pageSize = 100,
  signal?: AbortSignal,
): Promise<History> {
  const observations: HistoryObservation[] = []
  const seenTokens = new Set<string>()
  let continuationToken: string | undefined
  let historyMetadata: Pick<History, 'barcode' | 'store' | 'period'> | undefined
  let hasNextPage = true

  while (hasNextPage) {
    if (signal?.aborted) {
      throw new DOMException('The history request was aborted.', 'AbortError')
    }

    const params = new URLSearchParams({
      storeId,
      period,
      pageSize: String(pageSize),
    })
    if (continuationToken) {
      params.set('continuationToken', continuationToken)
    }

    const body = await fetchJson<HistoryResponse>(
      `/products/${encodeURIComponent(barcode)}/history?${params.toString()}`,
      signal,
    )
    const page = body.data
    historyMetadata ??= {
      barcode: page.barcode,
      store: page.store,
      period: page.period,
    }
    observations.push(...page.observations)

    if (!page.continuationToken) {
      hasNextPage = false
      continue
    }
    if (seenTokens.has(page.continuationToken)) {
      throw new Error('History pagination returned a repeated continuation token.')
    }
    seenTokens.add(page.continuationToken)
    continuationToken = page.continuationToken
  }

  if (!historyMetadata) {
    throw new Error('History returned no data.')
  }

  return {
    ...historyMetadata,
    observations,
  }
}
