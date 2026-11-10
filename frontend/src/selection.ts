export type ProductSelection = {
  barcode: string
  storeId: string | undefined
}

export function selectProduct(
  currentBarcode: string | undefined,
  currentStoreId: string | undefined,
  nextBarcode: string,
): ProductSelection {
  return {
    barcode: nextBarcode,
    storeId: currentBarcode === nextBarcode ? currentStoreId : undefined,
  }
}
