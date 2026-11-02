import type { HistoryObservation } from './api'

export type ChartObservation = {
  timestamp: number
  priceValue: number
  observedDate: string
  originalPrice: string
  currency: string
  sourceObservationId: string
}

export function toChartObservations(
  observations: HistoryObservation[],
): ChartObservation[] {
  return observations.map((observation) => {
    const [year, month, day] = observation.observedDate
      .split('-')
      .map(Number)
    return {
      timestamp: Date.UTC(year, month - 1, day),
      priceValue: Number(observation.price),
      observedDate: observation.observedDate,
      originalPrice: observation.price,
      currency: observation.currency,
      sourceObservationId: observation.sourceObservationId,
    }
  })
}

export function formatUtcDate(timestamp: number): string {
  return new Date(timestamp).toISOString().slice(0, 10)
}

export function formatEuroTick(value: number): string {
  return `€${value.toFixed(2).replace(/\.?0+$/, '')}`
}

export function getPriceAxis(prices: number[]): {
  domain: [number, number]
  ticks: number[]
} {
  const cents = prices.map((price) => Math.round(price * 100))
  const minCents = Math.min(...cents)
  const maxCents = Math.max(...cents)
  const range = maxCents - minCents
  const visibleRange = range || Math.max(Math.abs(minCents) * 0.2, 20)
  const roughStep = visibleRange / 4
  const magnitude = Math.max(1, 10 ** Math.floor(Math.log10(roughStep)))
  const normalizedStep = roughStep / magnitude
  const step = Math.ceil(
    (normalizedStep <= 1
      ? 1
      : normalizedStep <= 2
        ? 2
        : normalizedStep <= 2.5
          ? 2.5
          : normalizedStep <= 5
            ? 5
            : 10) * magnitude,
  )
  let lower = Math.floor((minCents - step * 0.5) / step) * step
  let upper = Math.ceil((maxCents + step * 0.5) / step) * step
  if ((upper - lower) / step < 3) {
    lower = Math.floor(minCents / step) * step - step
    upper = lower + step * 4
  }
  const ticks: number[] = []
  for (let tick = lower; tick <= upper + step / 2; tick += step) {
    ticks.push(Number((tick / 100).toFixed(2)))
  }
  return {
    domain: [Number((lower / 100).toFixed(2)), Number((upper / 100).toFixed(2))],
    ticks,
  }
}
