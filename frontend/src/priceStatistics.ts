import Big from 'big.js'
import type { HistoryObservation } from './api'

export type PriceStatistics = {
  latestPrice: string | null
  latestObservedDate: string | null
  minimumPrice: string | null
  maximumPrice: string | null
  meanPrice: string | null
  observationCount: number
}

/**
 * Same-date latest observations use the lexicographically greatest source ID
 * as a deterministic tie-breaker; this does not imply a time ordering.
 */
export function calculatePriceStatistics(
  observations: HistoryObservation[],
): PriceStatistics {
  if (observations.length === 0) {
    return {
      latestPrice: null,
      latestObservedDate: null,
      minimumPrice: null,
      maximumPrice: null,
      meanPrice: null,
      observationCount: 0,
    }
  }

  let latest = observations[0]
  let minimum = observations[0]
  let maximum = observations[0]
  let total = new Big(observations[0].price)

  for (const observation of observations.slice(1)) {
    const price = new Big(observation.price)
    total = total.plus(price)

    if (
      observation.observedDate > latest.observedDate ||
      (observation.observedDate === latest.observedDate &&
        observation.sourceObservationId > latest.sourceObservationId)
    ) {
      latest = observation
    }
    if (price.lt(new Big(minimum.price))) {
      minimum = observation
    }
    if (price.gt(new Big(maximum.price))) {
      maximum = observation
    }
  }

  return {
    latestPrice: latest.price,
    latestObservedDate: latest.observedDate,
    minimumPrice: minimum.price,
    maximumPrice: maximum.price,
    meanPrice: total.div(observations.length).toFixed(2, Big.roundHalfUp),
    observationCount: observations.length,
  }
}
