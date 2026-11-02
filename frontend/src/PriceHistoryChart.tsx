import {
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
import type { HistoryObservation } from './api'
import {
  type ChartObservation,
  formatUtcDate,
  formatEuroTick,
  getPriceAxis,
  toChartObservations,
} from './priceHistoryChartData'

function HistoryTooltip({
  active,
  payload,
}: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload?.length) {
    return null
  }

  const observation = payload[0].payload as ChartObservation
  return (
    <div className="chart-tooltip">
      <strong>{observation.observedDate}</strong>
      <span>
        {observation.originalPrice} {observation.currency}
      </span>
    </div>
  )
}

export function PriceHistoryChart({
  observations,
}: {
  observations: HistoryObservation[]
}) {
  const data = toChartObservations(observations)
  if (data.length === 0) {
    return null
  }

  const timestamps = data.map((observation) => observation.timestamp)
  const prices = data.map((observation) => observation.priceValue)
  const minTimestamp = Math.min(...timestamps)
  const maxTimestamp = Math.max(...timestamps)
  const timePadding =
    minTimestamp === maxTimestamp
      ? 24 * 60 * 60 * 1000
      : Math.max((maxTimestamp - minTimestamp) * 0.05, 24 * 60 * 60 * 1000)
  const priceAxis = getPriceAxis(prices)

  return (
    <div className="chart-container" aria-label="Historical price observations">
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 16, right: 24, bottom: 18, left: 24 }}>
          <XAxis
            dataKey="timestamp"
            domain={[minTimestamp - timePadding, maxTimestamp + timePadding]}
            tickFormatter={formatUtcDate}
            tickMargin={10}
            minTickGap={24}
            type="number"
            name="Date"
          />
          <YAxis
            dataKey="priceValue"
            domain={priceAxis.domain}
            ticks={priceAxis.ticks}
            tickFormatter={formatEuroTick}
            tickMargin={8}
            width={56}
            type="number"
            name="Price"
          />
          <Tooltip content={<HistoryTooltip />} />
          <Scatter
            data={data}
            fill="#26735d"
            fillOpacity={0.9}
            shape="circle"
            stroke="#ffffff"
            strokeWidth={2}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
