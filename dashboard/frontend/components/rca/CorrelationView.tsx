'use client'

import { useMemo } from 'react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { RCAResult } from '@/types/rca'

interface CorrelationViewProps {
  rcaResults: RCAResult[]
}

interface CorrelationNode {
  id: string
  type: 'anomaly' | 'cause'
  label: string
  confidence?: number
}

interface CorrelationEdge {
  source: string
  target: string
  weight: number
  type: 'temporal' | 'lineage' | 'pattern'
}

export default function CorrelationView({ rcaResults }: CorrelationViewProps) {
  const { nodes, edges } = useMemo(() => {
    const correlationNodes: CorrelationNode[] = []
    const correlationEdges: CorrelationEdge[] = []

    // Build nodes from RCA results
    rcaResults.forEach((result) => {
      // Add anomaly node
      correlationNodes.push({
        id: result.anomaly_id,
        type: 'anomaly',
        label: `${result.table_name}${result.column_name ? `.${result.column_name}` : ''}`,
      })

      // Add cause nodes and edges
      result.probable_causes.forEach((cause) => {
        const causeNodeId = `cause-${cause.cause_id}`
        
        // Add cause node if not already present
        if (!correlationNodes.find((n) => n.id === causeNodeId)) {
          correlationNodes.push({
            id: causeNodeId,
            type: 'cause',
            label: cause.cause_type,
            confidence: cause.confidence_score,
          })
        }

        // Add edge from anomaly to cause
        correlationEdges.push({
          source: result.anomaly_id,
          target: causeNodeId,
          weight: cause.confidence_score,
          type: 'pattern',
        })

        // Add edges between causes if they share affected assets
        cause.affected_assets.forEach((asset) => {
          result.probable_causes.forEach((otherCause) => {
            if (
              otherCause.cause_id !== cause.cause_id &&
              otherCause.affected_assets.includes(asset)
            ) {
              const otherCauseNodeId = `cause-${otherCause.cause_id}`
              correlationEdges.push({
                source: causeNodeId,
                target: otherCauseNodeId,
                weight: 0.5, // Shared asset correlation
                type: 'lineage',
              })
            }
          })
        })
      })
    })

    return { nodes: correlationNodes, edges: correlationEdges }
  }, [rcaResults])

  if (rcaResults.length === 0) {
    return (
      <Card>
        <CardBody>
          <div className="text-center py-12 text-slate-400">
            <p>No correlation data available</p>
            <p className="text-sm mt-2">Analyze anomalies to see correlations</p>
          </div>
        </CardBody>
      </Card>
    )
  }

  // Group nodes by type for display
  const anomalyNodes = nodes.filter((n) => n.type === 'anomaly')
  const causeNodes = nodes.filter((n) => n.type === 'cause')

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Correlation Network</h3>
        </CardHeader>
        <CardBody>
          <div className="space-y-6">
            {/* Legend */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-rose-500" />
                <span className="text-slate-300">Anomaly</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-cyan-500" />
                <span className="text-slate-300">Cause</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 bg-slate-500" />
                <span className="text-slate-300">Correlation</span>
              </div>
            </div>

            {/* Network visualization placeholder */}
            <div className="border border-surface-700/50 rounded-lg p-8 bg-surface-800/50 min-h-[400px] flex items-center justify-center">
              <div className="text-center text-slate-400">
                <p className="text-lg font-medium mb-2 text-white">Correlation Network Visualization</p>
                <p className="text-sm">
                  {nodes.length} nodes, {edges.length} connections
                </p>
                <p className="text-xs mt-4 text-slate-500">
                  Network graph visualization would be rendered here
                </p>
              </div>
            </div>

            {/* Node list */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Anomalies ({anomalyNodes.length})</h4>
                <div className="space-y-2">
                  {anomalyNodes.map((node) => (
                    <div
                      key={node.id}
                      className="flex items-center gap-2 p-2 bg-surface-700/50 border border-surface-700/50 rounded"
                    >
                      <div className="w-3 h-3 rounded-full bg-rose-500" />
                      <span className="text-sm text-white">{node.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Causes ({causeNodes.length})</h4>
                <div className="space-y-2">
                  {causeNodes
                    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                    .map((node) => (
                      <div
                        key={node.id}
                        className="flex items-center justify-between p-2 bg-surface-700/50 border border-surface-700/50 rounded"
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-cyan-500" />
                          <span className="text-sm text-white">{node.label}</span>
                        </div>
                        {node.confidence !== undefined && (
                          <Badge variant="default" size="sm">
                            {(node.confidence * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* Edge statistics */}
            <div className="border-t border-surface-700/50 pt-4">
              <h4 className="text-sm font-semibold text-white mb-3">Correlation Statistics</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-surface-700/50 rounded">
                  <p className="text-2xl font-bold text-white">{edges.length}</p>
                  <p className="text-xs text-slate-400">Total Connections</p>
                </div>
                <div className="text-center p-3 bg-surface-700/50 rounded">
                  <p className="text-2xl font-bold text-white">
                    {edges.filter((e) => e.type === 'pattern').length}
                  </p>
                  <p className="text-xs text-slate-400">Pattern Matches</p>
                </div>
                <div className="text-center p-3 bg-surface-700/50 rounded">
                  <p className="text-2xl font-bold text-white">
                    {edges.filter((e) => e.type === 'lineage').length}
                  </p>
                  <p className="text-xs text-slate-400">Lineage Links</p>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}

