import { useQuery } from '@tanstack/react-query'
import {
  fetchHistory,
  type HistoryPeriod,
  type Store,
} from './api'

const periods: { value: HistoryPeriod; label: string }[] = [
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: '1y', label: '1 year' },
  { value: 'all', label: 'All time' },
]

export function HistorySection({
  barcode,
  store,
  period,
  onPeriodChange,
}: {
  barcode: string
  store: Store
  period: HistoryPeriod
  onPeriodChange: (period: HistoryPeriod) => void
}) {
  const historyQuery = useQuery({
    queryKey: ['history', barcode, store.id, period],
    queryFn: ({ signal }) => fetchHistory(barcode, store.id, period, 100, signal),
  })

  const observations = [...(historyQuery.data?.observations ?? [])].sort(
    (left, right) =>
      left.observedDate.localeCompare(right.observedDate) ||
      left.sourceObservationId.localeCompare(right.sourceObservationId),
  )

  return (
    <section className="history" aria-labelledby="history-heading">
      <div className="history-heading">
        <div>
          <p className="eyebrow">Price history</p>
          <h2 id="history-heading">{store.name}</h2>
          <p className="history-address">{store.address}</p>
        </div>
        <p className="comparison-note">
          Historical recorded observations only. Prices are not current or
          guaranteed shelf prices.
        </p>
      </div>

      <fieldset className="period-controls">
        <legend>Observation period</legend>
        {periods.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name="history-period"
              value={option.value}
              checked={period === option.value}
              onChange={() => onPeriodChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </fieldset>

      {historyQuery.isLoading && (
        <p className="status" role="status">
          Loading price history...
        </p>
      )}

      {historyQuery.isError && (
        <div className="status status-error" role="alert">
          <p>{historyQuery.error.message}</p>
          <button type="button" onClick={() => historyQuery.refetch()}>
            Try again
          </button>
        </div>
      )}

      {historyQuery.isSuccess && observations.length === 0 && (
        <p className="status" role="status">
          No recorded observations for this store and period.
        </p>
      )}

      {historyQuery.isSuccess && observations.length > 0 && (
        <ol className="history-list">
          {observations.map((observation) => (
            <li key={observation.sourceObservationId}>
              <span>{observation.observedDate}</span>
              <strong>
                {observation.price} {observation.currency}
              </strong>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
