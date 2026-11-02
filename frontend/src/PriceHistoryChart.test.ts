import { describe, expect, it } from 'vitest'
import type { HistoryObservation } from './api'
import {
  formatEuroTick,
  formatUtcDate,
  getPriceAxis,
  toChartObservations,
} from './priceHistoryChartData'

function observation(
  sourceObservationId: string,
  observedDate: string,
  price: string,
): HistoryObservation {
  return {
    store: { id: '271', name: 'Auchan', address: 'Boulevard Lobau' },
    sourceObservationId,
    observedDate,
    price,
    currency: 'EUR',
  }
}

describe('toChartObservations', () => {
  it('uses UTC dates and preserves exact decimal prices', () => {
    const [result] = toChartObservations([
      observation('1', '2026-01-02', '1.2300'),
    ])

    expect(result.timestamp).toBe(Date.UTC(2026, 0, 2))
    expect(formatUtcDate(result.timestamp)).toBe('2026-01-02')
    expect(result.originalPrice).toBe('1.2300')
    expect(result.priceValue).toBe(1.23)
  })

  describe('getPriceAxis', () => {
    it('creates unique cent-based labels and includes observed prices', () => {
      const axis = getPriceAxis([3.77, 3.78, 4.12])
      const labels = axis.ticks.map(formatEuroTick)

      expect(new Set(labels).size).toBe(labels.length)
      expect(axis.domain[0]).toBeLessThanOrEqual(3.77)
      expect(axis.domain[1]).toBeGreaterThanOrEqual(4.12)
      expect(axis.ticks.length).toBeGreaterThanOrEqual(4)
      expect(axis.ticks.length).toBeLessThanOrEqual(6)
    })

    it('handles identical prices with multiple readable ticks', () => {
      const axis = getPriceAxis([3.77, 3.77])
      const labels = axis.ticks.map(formatEuroTick)

      expect(new Set(labels).size).toBe(labels.length)
      expect(axis.domain[0]).toBeLessThan(3.77)
      expect(axis.domain[1]).toBeGreaterThan(3.77)
    })
  })

  it('keeps observations that share a date', () => {
    const result = toChartObservations([
      observation('1', '2026-01-02', '1.20'),
      observation('2', '2026-01-02', '1.30'),
    ])

    expect(result).toHaveLength(2)
    expect(result[0].timestamp).toBe(result[1].timestamp)
    expect(result.map((item) => item.originalPrice)).toEqual(['1.20', '1.30'])
  })

  it('handles empty and single-observation histories', () => {
    expect(toChartObservations([])).toEqual([])
    expect(
      toChartObservations([observation('1', '2026-01-02', '2.50')]),
    ).toHaveLength(1)
  })
})
