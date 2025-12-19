'use client'

import { Badge } from '@/components/ui/Badge'
import { Card, CardBody } from '@/components/ui/Card'
import type { ColumnCheckRecommendation } from '@/types/recommendation'

interface ColumnRecommendationsProps {
  columnRecommendations: ColumnCheckRecommendation[]
  lowConfidenceColumns: ColumnCheckRecommendation[]
}

export default function ColumnRecommendations({
  columnRecommendations,
  lowConfidenceColumns,
}: ColumnRecommendationsProps) {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success'
    if (confidence >= 0.5) return 'warning'
    return 'default'
  }

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High'
    if (confidence >= 0.5) return 'Medium'
    return 'Low'
  }

  return (
    <div className="space-y-4">
      {/* High/Medium Confidence Recommendations */}
      {columnRecommendations.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-700 mb-2">Recommended Checks</h5>
          <div className="space-y-2">
            {columnRecommendations.map((col, idx) => (
              <Card key={idx} className="bg-green-50">
                <CardBody className="py-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-900">{col.column}</span>
                        <Badge variant="default" size="sm">
                          {col.data_type}
                        </Badge>
                        <Badge variant={getConfidenceColor(col.confidence)} size="sm">
                          {getConfidenceLabel(col.confidence)} ({Math.round(col.confidence * 100)}%)
                        </Badge>
                      </div>
                      {col.signals.length > 0 && (
                        <div className="text-xs text-gray-600 mb-2">
                          Signals: {col.signals.join(', ')}
                        </div>
                      )}
                      {col.suggested_checks.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {col.suggested_checks.map((check, checkIdx) => {
                            const checkName: string = typeof check === 'string' ? check : (typeof check === 'object' && check !== null && 'type' in check && typeof check.type === 'string' ? check.type : String(check))
                            return (
                              <Badge key={checkIdx} variant="info" size="sm">
                                {checkName}
                              </Badge>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Low Confidence Suggestions */}
      {lowConfidenceColumns.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-700 mb-2">
            Low Confidence (Manual Review Recommended)
          </h5>
          <div className="space-y-2">
            {lowConfidenceColumns.map((col, idx) => (
              <Card key={idx} className="bg-yellow-50">
                <CardBody className="py-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-gray-900">{col.column}</span>
                        <Badge variant="default" size="sm">
                          {col.data_type}
                        </Badge>
                        <Badge variant="default" size="sm">
                          Low ({Math.round(col.confidence * 100)}%)
                        </Badge>
                      </div>
                      {col.signals.length > 0 && (
                        <div className="text-xs text-gray-600 mb-2">
                          Signals: {col.signals.join(', ')}
                        </div>
                      )}
                      {col.suggested_checks.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {col.suggested_checks.map((check, checkIdx) => {
                            const checkName: string = typeof check === 'string' ? check : (typeof check === 'object' && check !== null && 'type' in check && typeof check.type === 'string' ? check.type : String(check))
                            return (
                              <Badge key={checkIdx} variant="default" size="sm">
                                {checkName}
                              </Badge>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      )}

      {columnRecommendations.length === 0 && lowConfidenceColumns.length === 0 && (
        <div className="text-sm text-gray-600 text-center py-4">
          No column recommendations available
        </div>
      )}
    </div>
  )
}

