'use client'

import { useMemo } from 'react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { DriftAlert } from '@/types/drift'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DriftAnalysisProps {
  alerts: DriftAlert[]
}

const COLORS = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
}

export default function DriftAnalysis({ alerts }: DriftAnalysisProps) {
  // Severity trends over time
  const severityTrends = useMemo(() => {
    const trends: Record<string, { date: string; low: number; medium: number; high: number }> = {}
    
    alerts.forEach((alert) => {
      const date = new Date(alert.timestamp || alert.detected_at || '').toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })
      
      if (!trends[date]) {
        trends[date] = { date, low: 0, medium: 0, high: 0 }
      }
      
      trends[date][alert.severity as 'low' | 'medium' | 'high']++
    })
    
    return Object.values(trends).sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    )
  }, [alerts])

  // Metric type breakdown
  const metricBreakdown = useMemo(() => {
    const breakdown: Record<string, { name: string; count: number; bySeverity: Record<string, number> }> = {}
    
    alerts.forEach((alert) => {
      const metric = alert.metric_name
      if (!breakdown[metric]) {
        breakdown[metric] = {
          name: metric,
          count: 0,
          bySeverity: { low: 0, medium: 0, high: 0 },
        }
      }
      breakdown[metric].count++
      breakdown[metric].bySeverity[alert.severity as 'low' | 'medium' | 'high']++
    })
    
    return Object.values(breakdown)
      .sort((a, b) => b.count - a.count)
      .slice(0, 10) // Top 10
  }, [alerts])

  // Table-level drift patterns
  const tablePatterns = useMemo(() => {
    const patterns: Record<string, { table: string; count: number; severity: string }> = {}
    
    alerts.forEach((alert) => {
      const table = alert.table_name
      if (!patterns[table]) {
        patterns[table] = {
          table,
          count: 0,
          severity: alert.severity,
        }
      }
      patterns[table].count++
      // Use highest severity
      const severityOrder = { high: 3, medium: 2, low: 1 }
      if (severityOrder[alert.severity as keyof typeof severityOrder] > 
          severityOrder[patterns[table].severity as keyof typeof severityOrder]) {
        patterns[table].severity = alert.severity
      }
    })
    
    return Object.values(patterns)
      .sort((a, b) => b.count - a.count)
      .slice(0, 10) // Top 10
  }, [alerts])

  if (alerts.length === 0) {
    return (
      <Card>
        <CardBody>
          <p className="text-center text-gray-500 py-8">No drift data available for analysis</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Severity Trends Over Time */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-gray-900">Severity Trends Over Time</h3>
        </CardHeader>
        <CardBody>
          {severityTrends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={severityTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="low" stackId="severity" fill={COLORS.low} name="Low" />
                <Bar dataKey="medium" stackId="severity" fill={COLORS.medium} name="Medium" />
                <Bar dataKey="high" stackId="severity" fill={COLORS.high} name="High" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-gray-500">
              No trend data available
            </div>
          )}
        </CardBody>
      </Card>

      {/* Metric Type Breakdown */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-gray-900">Metric Type Breakdown</h3>
        </CardHeader>
        <CardBody>
          {metricBreakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={metricBreakdown} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={150} />
                <Tooltip />
                <Legend />
                <Bar dataKey="bySeverity.low" stackId="metric" fill={COLORS.low} name="Low" />
                <Bar dataKey="bySeverity.medium" stackId="metric" fill={COLORS.medium} name="Medium" />
                <Bar dataKey="bySeverity.high" stackId="metric" fill={COLORS.high} name="High" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[400px] text-gray-500">
              No metric breakdown data available
            </div>
          )}
        </CardBody>
      </Card>

      {/* Table Patterns */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-gray-900">Top Affected Tables</h3>
        </CardHeader>
        <CardBody>
          {tablePatterns.length > 0 ? (
            <div className="space-y-3">
              {tablePatterns.map((pattern, index) => (
                <div
                  key={pattern.table}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium text-gray-500 w-6">#{index + 1}</span>
                    <div>
                      <p className="font-medium text-gray-900">{pattern.table}</p>
                      <p className="text-sm text-gray-500">{pattern.count} drift event(s)</p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      pattern.severity === 'high'
                        ? 'error'
                        : pattern.severity === 'medium'
                        ? 'warning'
                        : 'success'
                    }
                  >
                    {pattern.severity}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">No table patterns available</div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

