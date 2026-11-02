export type Product = {
  barcode: string
  name: string
}

type ProductsResponse = {
  data: Product[]
}

type ErrorResponse = {
  error?: {
    message?: string
  }
}

export async function fetchProducts(): Promise<Product[]> {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '')
  if (!apiBaseUrl) {
    throw new Error(
      'The API base URL is not configured. Set VITE_API_BASE_URL in frontend/.env.local.',
    )
  }

  const response = await fetch(`${apiBaseUrl}/products`)
  if (!response.ok) {
    let message = `Unable to load products (HTTP ${response.status}).`
    try {
      const body = (await response.json()) as ErrorResponse
      if (body.error?.message) {
        message = body.error.message
      }
    } catch {}
    throw new Error(message)
  }

  const body = (await response.json()) as ProductsResponse
  return body.data
}
