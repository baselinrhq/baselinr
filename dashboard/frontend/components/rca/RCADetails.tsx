'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ExternalLink, RefreshCw, X, ChevronDown, ChevronUp } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { getRCAResult, reanalyzeAnomaly, dismissRCAResult } from '@/lib/api/rca'
import type { RCAResult, ProbableCause } from '@/types/rca'
import Link from 'next/link'

interface RCADetailsProps {
  anomalyId: string
  isOpen: boolean
  onClose: () => void
}

export default function RCADetails({ anomalyId, isOpen, onClose }: RCADetailsProps) {
  const queryClient = useQueryClient()
  const [expandedCauses, setExpandedCauses] = useState<Set<string>>(new Set())
  const [dismissReason, setDismissReason] = useState('')

  const { data: rcaResult, isLoading } = useQuery<RCAResult>({
    queryKey: ['rca-result', anomalyId],
    queryFn: () => getRCAResult(anomalyId),
    enabled: isOpen && !!anomalyId,
  })

  const reanalyzeMutation = useMutation({
    mutationFn: () => reanalyzeAnomaly(anomalyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rca-result', anomalyId] })
      queryClient.invalidateQueries({ queryKey: ['rca-list'] })
    },
  })

  const dismissMutation = useMutation({
    mutationFn: (reason?: string) => dismissRCAResult(anomalyId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rca-result', anomalyId] })
      queryClient.invalidateQueries({ queryKey: ['rca-list'] })
      queryClient.invalidateQueries({ queryKey: ['rca-statistics'] })
      onClose()
    },
  })

  const toggleCauseExpansion = (causeId: string) => {
    const newExpanded = new Set(expandedCauses)
    if (newExpanded.has(causeId)) {
      newExpanded.delete(causeId)
    } else {
      newExpanded.add(causeId)
    }
    setExpandedCauses(newExpanded)
  }

  if (!isOpen) return null

  const tableName = rcaResult?.schema_name
    ? `${rcaResult.schema_name}.${rcaResult.table_name}`
    : rcaResult?.table_name

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Root Cause Analysis Details"
      size="xl"
    >
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      ) : !rcaResult ? (
        <div className="text-center py-8 text-gray-500">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p>Failed to load RCA details</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Anomaly Information */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold text-gray-900">Anomaly Information</h3>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Table</p>
                  <p className="font-medium text-gray-900">{tableName}</p>
                </div>
                {rcaResult.column_name && (
                  <div>
                    <p className="text-sm text-gray-500">Column</p>
                    <p className="font-medium text-gray-900">{rcaResult.column_name}</p>
                  </div>
                )}
                {rcaResult.metric_name && (
                  <div>
                    <p className="text-sm text-gray-500">Metric</p>
                    <p className="font-medium text-gray-900">{rcaResult.metric_name}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <Badge
                    variant={
                      rcaResult.rca_status === 'analyzed'
                        ? 'success'
                        : rcaResult.rca_status === 'pending'
                        ? 'warning'
                        : 'default'
                    }
                  >
                    {rcaResult.rca_status}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Analyzed At</p>
                  <p className="font-medium text-gray-900">
                    {new Date(rcaResult.analyzed_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Anomaly ID</p>
                  <p className="font-mono text-xs text-gray-600">{rcaResult.anomaly_id}</p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200">
                <Link
                  href={`/tables/${rcaResult.table_name}`}
                  className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-800"
                >
                  View table details
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </div>
            </CardBody>
          </Card>

          {/* Probable Causes */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  Probable Causes ({rcaResult.probable_causes.length})
                </h3>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => reanalyzeMutation.mutate()}
                    disabled={reanalyzeMutation.isPending}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Reanalyze
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardBody>
              {rcaResult.probable_causes.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No probable causes identified</p>
              ) : (
                <div className="space-y-4">
                  {rcaResult.probable_causes
                    .sort((a, b) => b.confidence_score - a.confidence_score)
                    .map((cause) => (
                      <CauseCard
                        key={cause.cause_id}
                        cause={cause}
                        isExpanded={expandedCauses.has(cause.cause_id)}
                        onToggle={() => toggleCauseExpansion(cause.cause_id)}
                      />
                    ))}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Impact Analysis */}
          {rcaResult.impact_analysis && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-gray-900">Impact Analysis</h3>
              </CardHeader>
              <CardBody>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">Blast Radius Score</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{ width: `${rcaResult.impact_analysis.blast_radius_score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {(rcaResult.impact_analysis.blast_radius_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  {rcaResult.impact_analysis.upstream_affected.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">Upstream Affected</p>
                      <div className="flex flex-wrap gap-2">
                        {rcaResult.impact_analysis.upstream_affected.map((asset) => (
                          <Badge key={asset} variant="info" size="sm">
                            {asset}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {rcaResult.impact_analysis.downstream_affected.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">Downstream Affected</p>
                      <div className="flex flex-wrap gap-2">
                        {rcaResult.impact_analysis.downstream_affected.map((asset) => (
                          <Badge key={asset} variant="warning" size="sm">
                            {asset}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Actions */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold text-gray-900">Actions</h3>
            </CardHeader>
            <CardBody>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dismiss Reason (optional)
                  </label>
                  <textarea
                    value={dismissReason}
                    onChange={(e) => setDismissReason(e.target.value)}
                    placeholder="Enter reason for dismissing this analysis..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={3}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="error"
                    onClick={() => dismissMutation.mutate(dismissReason || undefined)}
                    disabled={dismissMutation.isPending}
                  >
                    <X className="w-4 h-4 mr-2" />
                    Dismiss Analysis
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </Modal>
  )
}

interface CauseCardProps {
  cause: ProbableCause
  isExpanded: boolean
  onToggle: () => void
}

function CauseCard({ cause, isExpanded, onToggle }: CauseCardProps) {
  const confidenceColor =
    cause.confidence_score >= 0.7
      ? 'success'
      : cause.confidence_score >= 0.4
      ? 'warning'
      : 'default'

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Badge variant={confidenceColor} size="sm">
              {(cause.confidence_score * 100).toFixed(0)}% confidence
            </Badge>
            <span className="text-sm font-medium text-gray-900">{cause.cause_type}</span>
          </div>
          <p className="text-sm text-gray-700 mb-2">{cause.description}</p>
          {cause.affected_assets.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {cause.affected_assets.map((asset) => (
                <Badge key={asset} variant="info" size="sm">
                  {asset}
                </Badge>
              ))}
            </div>
          )}
          {cause.suggested_action && (
            <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
              <span className="font-medium">Suggested Action:</span> {cause.suggested_action}
            </div>
          )}
        </div>
        <button
          onClick={onToggle}
          className="ml-4 text-gray-400 hover:text-gray-600"
        >
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
      </div>
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs font-medium text-gray-500 mb-2">Evidence</p>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
            {JSON.stringify(cause.evidence, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

