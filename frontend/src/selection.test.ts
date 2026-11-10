import { describe, expect, it } from 'vitest'
import { selectProduct } from './selection'

describe('selectProduct', () => {
  it('clears the store when changing products', () => {
    expect(selectProduct('product-a', 'store-1', 'product-b')).toEqual({
      barcode: 'product-b',
      storeId: undefined,
    })
  })

  it('keeps the store when reselecting the same product', () => {
    expect(selectProduct('product-a', 'store-1', 'product-a')).toEqual({
      barcode: 'product-a',
      storeId: 'store-1',
    })
  })
})
