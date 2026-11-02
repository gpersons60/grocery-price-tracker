import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchProducts, type Product } from './api'
import './App.css'

function ProductCard({ product }: { product: Product }) {
  return (
    <article className="product-card">
      <h2>{product.name}</h2>
      <p className="barcode">Barcode: {product.barcode}</p>
    </article>
  )
}

function App() {
  const [search, setSearch] = useState('')
  const productsQuery = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
  })

  const filteredProducts = (productsQuery.data ?? []).filter((product) => {
    const searchTerm = search.trim().toLocaleLowerCase()
    return (
      product.name.toLocaleLowerCase().includes(searchTerm) ||
      product.barcode.toLocaleLowerCase().includes(searchTerm)
    )
  })

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Nancy, France</p>
        <h1>Historical grocery price tracker</h1>
        <p className="intro">
          Browse products with recorded observations from local physical stores.
          These are historical observations, not live prices.
        </p>
      </header>

      <section className="catalogue" aria-labelledby="catalogue-heading">
        <div className="catalogue-heading">
          <div>
            <p className="eyebrow">Product catalogue</p>
            <h2 id="catalogue-heading">Find a product</h2>
          </div>
          {productsQuery.data && (
            <span className="result-count">
              {productsQuery.data.length} products
            </span>
          )}
        </div>

        {productsQuery.isLoading && (
          <p className="status" role="status">
            Loading products...
          </p>
        )}

        {productsQuery.isError && (
          <div className="status status-error" role="alert">
            <p>{productsQuery.error.message}</p>
            <button type="button" onClick={() => productsQuery.refetch()}>
              Try again
            </button>
          </div>
        )}

        {productsQuery.isSuccess && (
          <>
            <label className="search-label" htmlFor="product-search">
              Search by product name or barcode
            </label>
            <input
              id="product-search"
              className="search-input"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="e.g. Barilla or 8076808890015"
            />

            {filteredProducts.length > 0 ? (
              <div className="product-grid">
                {filteredProducts.map((product) => (
                  <ProductCard key={product.barcode} product={product} />
                ))}
              </div>
            ) : (
              <p className="status" role="status">
                No products match “{search}”.
              </p>
            )}
          </>
        )}
      </section>
    </main>
  )
}

export default App
