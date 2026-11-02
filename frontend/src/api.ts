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

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`)
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
