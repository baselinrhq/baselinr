'use client'

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface TrendData {
  timestamp: string
  value: number
}

interface TrendChartsProps {
  runTrend: TrendData[]
  driftTrend: TrendData[]
  validationTrend: TrendData[]
}

export default function TrendCharts({
  runTrend,
  driftTrend,
  validationTrend,
}: TrendChartsProps) {
  // Combine all trends into a single dataset for the chart
  // Group by date and merge values
  const combineTrends = () => {
    const dataMap = new Map<string, { runs: number; drift: number; validation: number }>()

    // Helper to extract date string from timestamp
    const getDateString = (timestamp: string): string => {
      try {
        const date = new Date(timestamp)
        if (isNaN(date.getTime())) {
          return timestamp.split('T')[0] // Fallback to string split
        }
        return date.toISOString().split('T')[0]
      } catch {
        return timestamp.split('T')[0]
      }
    }

    // Process run trend
    if (runTrend && runTrend.length > 0) {
      runTrend.forEach((item) => {
        const date = getDateString(item.timestamp)
        if (!dataMap.has(date)) {
          dataMap.set(date, { runs: 0, drift: 0, validation: 0 })
        }
        const existing = dataMap.get(date)!
        existing.runs = item.value || 0
      })
    }

    // Process drift trend
    if (driftTrend && driftTrend.length > 0) {
      driftTrend.forEach((item) => {
        const date = getDateString(item.timestamp)
        if (!dataMap.has(date)) {
          dataMap.set(date, { runs: 0, drift: 0, validation: 0 })
        }
        const existing = dataMap.get(date)!
        existing.drift = item.value || 0
      })
    }

    // Process validation trend
    if (validationTrend && validationTrend.length > 0) {
      validationTrend.forEach((item) => {
        const date = getDateString(item.timestamp)
        if (!dataMap.has(date)) {
          dataMap.set(date, { runs: 0, drift: 0, validation: 0 })
        }
        const existing = dataMap.get(date)!
        existing.validation = item.value || 0
      })
    }

    // Convert to array and sort by date
    return Array.from(dataMap.entries())
      .map(([date, values]) => ({
        date,
        timestamp: date,
        runs: values.runs,
        drift: values.drift,
        validation: values.validation,
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
  }

  const chartData = combineTrends()

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } catch {
      return dateStr
    }
  }

  const hasData = chartData.length > 0 && chartData.some((d) => d.runs > 0 || d.drift > 0 || d.validation > 0)

  return (
    <div className="glass-card p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Trends Overview</h2>
      <div className="h-64">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                stroke="#94a3b8"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                yAxisId="left"
                stroke="#94a3b8"
                style={{ fontSize: '12px' }}
                label={{ value: 'Count', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#94a3b8"
                style={{ fontSize: '12px' }}
                label={{ value: 'Pass Rate %', angle: 90, position: 'insideRight', fill: '#94a3b8' }}
                domain={[0, 100]}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || !payload.length) {
                    return null
                  }
                  
                  interface TooltipPayload {
                    dataKey?: string
                    name?: string
                    value?: number | string
                    color?: string
                  }
                  
                  return (
                    <div
                      style={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        padding: '12px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                      }}
                    >
                      <p style={{ marginBottom: '8px', fontWeight: '600', color: '#f1f5f9' }}>
                        {formatDate(label as string)}
                      </p>
                      {payload.map((entry: TooltipPayload, index: number) => {
                        const dataKey = entry.dataKey
                        let displayLabel = entry.name || ''
                        let displayValue: string | number = entry.value || 0
                        
                        // Determine label and format based on dataKey
                        if (dataKey === 'validation') {
                          displayLabel = 'Validation Pass Rate'
                          displayValue = `${Number(displayValue).toFixed(1)}%`
                        } else if (dataKey === 'runs') {
                          displayLabel = 'Runs'
                          displayValue = Number(displayValue).toString()
                        } else if (dataKey === 'drift') {
                          displayLabel = 'Drift Events'
                          displayValue = Number(displayValue).toString()
                        }
                        
                        return (
                          <p key={index} style={{ color: entry.color, margin: '4px 0', fontSize: '13px' }}>
                            {displayLabel}: <span style={{ fontWeight: '600' }}>{displayValue}</span>
                          </p>
                        )
                      })}
                    </div>
                  )
                }}
              />
              <Legend 
                wrapperStyle={{ color: '#94a3b8' }}
                formatter={(value) => <span style={{ color: '#cbd5e1' }}>{value}</span>}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="runs"
                fill="#06b6d4"
                fillOpacity={0.2}
                stroke="#06b6d4"
                strokeWidth={2}
                name="Runs"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="drift"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 3, fill: '#f59e0b' }}
                name="Drift Events"
              />
              {validationTrend.length > 0 && (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="validation"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#22c55e' }}
                  strokeDasharray="5 5"
                  name="Validation Pass Rate"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-500">No trend data available</p>
          </div>
        )}
      </div>
    </div>
  )
}
