'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle2, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import ColumnRecommendations from './ColumnRecommendations'
import type { TableRecommendation } from '@/types/recommendation'

interface RecommendationCardProps {
  recommendation: TableRecommendation
  isSelected: boolean
  onSelect: () => void
  onApply: () => void
}

export default function RecommendationCard({
  recommendation,
  isSelected,
  onSelect,
  onApply,
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showColumns, setShowColumns] = useState(false)

  const confidenceColor =
    recommendation.confidence >= 0.8
      ? 'success'
      : recommendation.confidence >= 0.5
      ? 'warning'
      : 'default'

  const confidenceLabel =
    recommendation.confidence >= 0.8
      ? 'High'
      : recommendation.confidence >= 0.5
      ? 'Medium'
      : 'Low'

  return (
    <Card className={isSelected ? 'ring-2 ring-primary-500' : ''}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={onSelect}
                className="w-4 h-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <CardTitle className="text-lg">
                {recommendation.schema && (
                  <span className="text-gray-500">{recommendation.schema}.</span>
                )}
                {recommendation.table}
              </CardTitle>
              {recommendation.database && (
                <Badge variant="default" size="sm">
                  {recommendation.database}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              <Badge variant={confidenceColor} size="sm">
                {confidenceLabel} Confidence ({Math.round(recommendation.confidence * 100)}%)
              </Badge>
              <Badge variant="default" size="sm">
                Score: {recommendation.score.toFixed(2)}
              </Badge>
              {recommendation.column_recommendations.length > 0 && (
                <Badge variant="info" size="sm">
                  {recommendation.column_recommendations.length} Column Checks
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="secondary"
              size="sm"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-1" />
                  Less
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-1" />
                  More
                </>
              )}
            </Button>
            <Button onClick={onApply} variant="primary" size="sm">
              Apply
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardBody className="space-y-4">
          {/* Reasons */}
          {recommendation.reasons.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Reasons
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                {recommendation.reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {recommendation.warnings.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                Warnings
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-yellow-700">
                {recommendation.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Metadata */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
            {recommendation.query_count > 0 && (
              <div>
                <div className="text-xs text-gray-600">Query Count</div>
                <div className="text-sm font-semibold text-gray-900">
                  {recommendation.query_count}
                </div>
              </div>
            )}
            {recommendation.queries_per_day > 0 && (
              <div>
                <div className="text-xs text-gray-600">Queries/Day</div>
                <div className="text-sm font-semibold text-gray-900">
                  {recommendation.queries_per_day.toFixed(1)}
                </div>
              </div>
            )}
            {recommendation.row_count !== null && recommendation.row_count !== undefined && (
              <div>
                <div className="text-xs text-gray-600">Row Count</div>
                <div className="text-sm font-semibold text-gray-900">
                  {recommendation.row_count?.toLocaleString() || '—'}
                </div>
              </div>
            )}
            {recommendation.column_count > 0 && (
              <div>
                <div className="text-xs text-gray-600">Columns</div>
                <div className="text-sm font-semibold text-gray-900">
                  {recommendation.column_count}
                </div>
              </div>
            )}
            {recommendation.last_query_days_ago !== null && recommendation.last_query_days_ago !== undefined && (
              <div>
                <div className="text-xs text-gray-600">Last Query</div>
                <div className="text-sm font-semibold text-gray-900">
                  {recommendation.last_query_days_ago} days ago
                </div>
              </div>
            )}
          </div>

          {/* Suggested Checks */}
          {recommendation.suggested_checks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Suggested Checks</h4>
              <div className="flex flex-wrap gap-2">
                {recommendation.suggested_checks.map((check, idx) => (
                  <Badge key={idx} variant="default" size="sm">
                    {check}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Column Recommendations */}
          {(recommendation.column_recommendations.length > 0 || recommendation.low_confidence_columns.length > 0) && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-gray-900">Column Recommendations</h4>
                <Button
                  onClick={() => setShowColumns(!showColumns)}
                  variant="secondary"
                  size="sm"
                >
                  {showColumns ? 'Hide' : 'Show'} Columns
                </Button>
              </div>
              {showColumns && (
                <ColumnRecommendations
                  columnRecommendations={recommendation.column_recommendations}
                  lowConfidenceColumns={recommendation.low_confidence_columns}
                />
              )}
            </div>
          )}
        </CardBody>
      )}
    </Card>
  )
}

