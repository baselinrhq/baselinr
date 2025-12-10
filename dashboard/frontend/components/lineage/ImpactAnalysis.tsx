'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, TrendingUp, Database, Download, CheckCircle } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { getLineageImpact } from '@/lib/api/lineage'
import type { LineageImpactResponse } from '@/types/lineage'

interface ImpactAnalysisProps {
  table: string
  schema?: string
  isOpen?: boolean
  onClose?: () => void
}

export default function ImpactAnalysis({
  table,
  schema,
  isOpen = true,
  onClose,
}: ImpactAnalysisProps) {
  const { data: impact, isLoading, error } = useQuery<LineageImpactResponse>({
    queryKey: ['lineage-impact', table, schema],
    queryFn: () => getLineageImpact(table, schema, true),
    enabled: !!table && isOpen,
  })

  const handleExport = () => {
    if (impact) {
      const dataStr = JSON.stringify(impact, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `lineage-impact-${table}-${Date.now()}.json`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  if (!isOpen || !table) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-gray-500" />
            <h3 className="text-lg font-semibold text-gray-900">Impact Analysis</h3>
          </div>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
            >
              Close
            </Button>
          )}
        </div>
      </CardHeader>
      <CardBody>
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        )}

        {error && (
          <div className="text-center py-8 text-gray-500">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <p>Failed to load impact analysis</p>
          </div>
        )}

        {impact && (
          <div className="space-y-6">
            {/* Impact Score */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Impact Score</span>
                <Badge
                  variant={impact.impact_score > 0.7 ? 'error' : impact.impact_score > 0.4 ? 'warning' : 'success'}
                >
                  {(impact.impact_score * 100).toFixed(0)}%
                </Badge>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    impact.impact_score > 0.7
                      ? 'bg-red-600'
                      : impact.impact_score > 0.4
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                  }`}
                  style={{ width: `${impact.impact_score * 100}%` }}
                />
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">Affected Tables</div>
                <div className="text-2xl font-bold text-gray-900">{impact.affected_tables.length}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">Affected Metrics</div>
                <div className="text-2xl font-bold text-gray-900">{impact.affected_metrics}</div>
              </div>
            </div>

            {/* Affected Tables */}
            {impact.affected_tables.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Affected Downstream Tables
                </h4>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {impact.affected_tables.map((table) => (
                    <div
                      key={`${table.schema}.${table.table}`}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
                    >
                      <div>
                        <span className="font-medium text-gray-900">{table.table}</span>
                        {table.schema && (
                          <span className="text-gray-500 ml-2">{table.schema}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Drift Propagation */}
            {impact.drift_propagation.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Drift Propagation Path</h4>
                <div className="flex items-center gap-2 flex-wrap">
                  {impact.drift_propagation.map((nodeId, idx) => (
                    <div key={nodeId} className="flex items-center gap-2">
                      <Badge variant="info" size="sm">
                        {nodeId.split('.').pop()}
                      </Badge>
                      {idx < impact.drift_propagation.length - 1 && (
                        <span className="text-gray-400">→</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {impact.recommendations.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Recommendations
                </h4>
                <ul className="space-y-2">
                  {impact.recommendations.map((rec) => (
                    <li key={rec} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="text-primary-600 mt-1">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Export Button */}
            <div className="pt-4 border-t border-gray-200">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                icon={<Download className="w-4 h-4" />}
              >
                Export Impact Report
              </Button>
            </div>
          </div>
        )}

        {impact && impact.affected_tables.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Database className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <p>No downstream dependencies found</p>
            <p className="text-xs mt-1">This table may be a source table</p>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

