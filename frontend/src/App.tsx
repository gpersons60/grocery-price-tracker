import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchComparison,
  fetchProducts,
  fetchStores,
  type Observation,
  type Product,
  type Store,
  type HistoryPeriod,
} from './api'
import { HistorySection } from './History'
import { selectProduct } from './selection'
import './App.css'

function ProductCard({
  product,
  isSelected,
  onSelect,
}: {
  product: Product
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <button
      className={`product-card${isSelected ? ' product-card-selected' : ''}`}
      type="button"
      aria-pressed={isSelected}
      onClick={onSelect}
    >
      <span className="product-name">{product.name}</span>
      <span className="barcode">Barcode: {product.barcode}</span>
    </button>
  )
}

function ComparisonCard({
  store,
  observation,
  isSelected,
  onSelect,
}: {
  store: Store
  observation: Observation | undefined
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <button
      className={`comparison-card${isSelected ? ' comparison-card-selected' : ''}`}
      type="button"
      aria-pressed={isSelected}
      onClick={onSelect}
    >
      <span className="store-heading">
        <span className="store-name">{store.name}</span>
        <span className="store-address">{store.address}</span>
      </span>
      {observation ? (
        <span className="observation">
          <span className="historical-label">Historical observation</span>
          <span className="price">
            {observation.price} {observation.currency}
          </span>
          <span className="observation-date">
            Observed on {observation.observedDate}
          </span>
        </span>
      ) : (
        <span className="no-price">No recorded price</span>
      )}
    </button>
  )
}

function App() {
  const [search, setSearch] = useState('')
  const [selectedBarcode, setSelectedBarcode] = useState<string>()
  const [selectedStoreId, setSelectedStoreId] = useState<string>()
  const [historyPeriod, setHistoryPeriod] = useState<HistoryPeriod>('90d')
  const productsQuery = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
    staleTime: 60 * 60 * 1000,
  })
  const storesQuery = useQuery({
    queryKey: ['stores'],
    queryFn: fetchStores,
    staleTime: 60 * 60 * 1000,
  })
  const selectedProduct = productsQuery.data?.find(
    (product) => product.barcode === selectedBarcode,
  )
  const comparisonQuery = useQuery({
    queryKey: ['comparison', selectedBarcode],
    queryFn: () => {
      if (!selectedBarcode) {
        throw new Error('Select a product to load its comparison.')
      }
      return fetchComparison(selectedBarcode)
    },
    enabled: Boolean(selectedBarcode),
    staleTime: 15 * 60 * 1000,
  })

  function handleProductSelect(barcode: string) {
    const selection = selectProduct(
      selectedBarcode,
      selectedStoreId,
      barcode,
    )
    setSelectedBarcode(selection.barcode)
    setSelectedStoreId(selection.storeId)
  }

  const searchTerm = search.trim().toLocaleLowerCase()
  const filteredProducts = (productsQuery.data ?? []).filter((product) => {
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
                  <ProductCard
                    key={product.barcode}
                    product={product}
                    isSelected={product.barcode === selectedBarcode}
                    onSelect={() => handleProductSelect(product.barcode)}
                  />
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

      {selectedProduct && (
        <section className="comparison" aria-labelledby="comparison-heading">
          <div className="comparison-heading">
            <div>
              <p className="eyebrow">Store comparison</p>
              <h2 id="comparison-heading">{selectedProduct.name}</h2>
            </div>
            <p className="comparison-note">
              Latest recorded observations by physical store. These are not
              current or guaranteed shelf prices, and are not ranked by cost.
            </p>
          </div>

          {comparisonQuery.isLoading && (
            <p className="status" role="status">
              Loading store observations...
            </p>
          )}

          {comparisonQuery.isError && (
            <div className="status status-error" role="alert">
              <p>{comparisonQuery.error.message}</p>
              <button type="button" onClick={() => comparisonQuery.refetch()}>
                Try again
              </button>
            </div>
          )}

          {storesQuery.isError && (
            <div className="status status-error" role="alert">
              <p>{storesQuery.error.message}</p>
              <button type="button" onClick={() => storesQuery.refetch()}>
                Try again
              </button>
            </div>
          )}

          {storesQuery.isLoading && (
            <p className="status" role="status">
              Loading store catalogue...
            </p>
          )}

          {comparisonQuery.isSuccess &&
            storesQuery.isSuccess &&
            comparisonQuery.data.barcode === selectedBarcode && (
              <div className="comparison-grid">
                {storesQuery.data.map((store) => (
                  <ComparisonCard
                    key={store.id}
                    store={store}
                    isSelected={store.id === selectedStoreId}
                    onSelect={() => setSelectedStoreId(store.id)}
                    observation={comparisonQuery.data.stores.find(
                      (observation) => observation.store.id === store.id,
                    )}
                  />
                ))}
              </div>
            )}
        </section>
      )}

      {selectedProduct &&
        selectedStoreId &&
        storesQuery.data &&
        storesQuery.data.some((store) => store.id === selectedStoreId) && (
          <HistorySection
            barcode={selectedProduct.barcode}
            store={
              storesQuery.data.find((store) => store.id === selectedStoreId)!
            }
            period={historyPeriod}
            onPeriodChange={setHistoryPeriod}
          />
        )}

      <footer className="attribution" aria-label="Data attribution">
        Historical price observations sourced from{' '}
        <a href="https://prices.openfoodfacts.org/">Open Prices by Open Food Facts</a>
        . Data is provided under the{' '}
        <a href="https://opendatacommons.org/licenses/odbl/">
          Open Database License (ODbL) 1.0
        </a>
        .
      </footer>
    </main>
  )
}

export default App
