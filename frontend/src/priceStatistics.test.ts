import { describe, expect, it } from 'vitest'
import type { HistoryObservation } from './api'
import { calculatePriceStatistics } from './priceStatistics'

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

describe('calculatePriceStatistics', () => {
  it('returns a clearly empty result for no observations', () => {
    expect(calculatePriceStatistics([])).toEqual({
      latestPrice: null,
      latestObservedDate: null,
      minimumPrice: null,
      maximumPrice: null,
      meanPrice: null,
      observationCount: 0,
    })
  })

  it('handles a single observation without changing its precision', () => {
    expect(
      calculatePriceStatistics([observation('1', '2026-01-02', '2.5000')]),
    ).toEqual({
      latestPrice: '2.5000',
      latestObservedDate: '2026-01-02',
      minimumPrice: '2.5000',
      maximumPrice: '2.5000',
      meanPrice: '2.50',
      observationCount: 1,
    })
  })

  it('selects the latest date from unsorted observations', () => {
    expect(
      calculatePriceStatistics([
        observation('later', '2026-01-03', '4.00'),
        observation('earlier', '2026-01-01', '1.00'),
        observation('middle', '2026-01-02', '2.00'),
      ]),
    ).toMatchObject({
      latestPrice: '4.00',
      latestObservedDate: '2026-01-03',
      minimumPrice: '1.00',
      maximumPrice: '4.00',
    })
  })

  it('uses the greatest source ID only as a same-date tie-breaker', () => {
    expect(
      calculatePriceStatistics([
        observation('source-b', '2026-01-03', '2.00'),
        observation('source-a', '2026-01-03', '3.00'),
      ]),
    ).toMatchObject({
      latestPrice: '2.00',
      latestObservedDate: '2026-01-03',
    })
  })

  it('calculates decimal min, max, and mean across same-date observations', () => {
    expect(
      calculatePriceStatistics([
        observation('1', '2026-01-02', '1.10'),
        observation('2', '2026-01-02', '2.20'),
        observation('3', '2026-01-01', '3.30'),
      ]),
    ).toMatchObject({
      minimumPrice: '1.10',
      maximumPrice: '3.30',
      meanPrice: '2.20',
      observationCount: 3,
    })
  })

  it('rounds a half-up mean to exactly two decimal places', () => {
    expect(
      calculatePriceStatistics([
        observation('1', '2026-01-01', '3.65'),
        observation('2', '2026-01-02', '3.66'),
        observation('3', '2026-01-03', '3.655'),
      ]).meanPrice,
    ).toBe('3.66')
  })

  it('calculates complete-period values from observations spanning pages', () => {
    const firstPage = [
      observation('1', '2026-01-01', '1.005'),
      observation('2', '2026-01-02', '9.995'),
    ]
    const secondPage = [
      observation('3', '2026-01-03', '2.000'),
      observation('4', '2026-01-04', '4.000'),
    ]

    expect(calculatePriceStatistics([...firstPage, ...secondPage])).toEqual({
      latestPrice: '4.000',
      latestObservedDate: '2026-01-04',
      minimumPrice: '1.005',
      maximumPrice: '9.995',
      meanPrice: '4.25',
      observationCount: 4,
    })
  })
})
