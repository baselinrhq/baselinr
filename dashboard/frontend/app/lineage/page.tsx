'use client'

/**
 * Enhanced lineage exploration interface
 */

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Download, GitBranch } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { getLineageGraph, getNodeDetails, getAllTables } from '@/lib/api/lineage'
import { getLineageGraphWithFilters } from '@/lib/api/lineage'
import type { LineageGraphResponse, TableInfoResponse, LineageFilters as LineageFiltersType, NodeDetailsResponse } from '@/types/lineage'
import type { GetLineageGraphParams } from '@/lib/api/lineage'
import LineageSearch from '@/components/lineage/LineageSearch'
import LineageFilters from '@/components/lineage/LineageFilters'
import EnhancedLineageViewer from '@/components/lineage/EnhancedLineageViewer'
import ImpactAnalysis from '@/components/lineage/ImpactAnalysis'
import ColumnLineageView from '@/components/lineage/ColumnLineageView'

function LineageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const [selectedTable, setSelectedTable] = useState<TableInfoResponse | null>(
    searchParams.get('table') ? {
      table: searchParams.get('table') || '',
      schema: searchParams.get('schema') || undefined,
    } : null
  )
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>(
    (searchParams.get('direction') as 'upstream' | 'downstream' | 'both') || 'both'
  )
  const [depth, setDepth] = useState(Number(searchParams.get('depth')) || 3)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0)
  const [layout, setLayout] = useState<'hierarchical' | 'circular' | 'force-directed' | 'breadth-first' | 'grid'>('hierarchical')
  const [filters, setFilters] = useState<LineageFiltersType>({})
  const [viewMode] = useState<'table' | 'column'>('table')
  const [selectedColumn] = useState<string>('')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [showImpactPanel, setShowImpactPanel] = useState(false)
  const [showNodeDetails, setShowNodeDetails] = useState(false)

  const [graph, setGraph] = useState<LineageGraphResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch lineage when parameters change
  useEffect(() => {
    if (!selectedTable) {
      setGraph(null)
      return
    }

    const fetchLineage = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const params = {
          table: selectedTable.table,
          schema: selectedTable.schema,
          direction,
          depth,
          confidenceThreshold,
          ...filters,
        }
        
        const data = viewMode === 'column' && selectedColumn
          ? await getLineageGraph({
              ...params,
              column: selectedColumn,
            } as GetLineageGraphParams & { column: string })
          : await getLineageGraphWithFilters(params)
        
        setGraph(data)

        // Update URL
        const urlParams = new URLSearchParams({
          table: selectedTable.table,
          ...(selectedTable.schema && { schema: selectedTable.schema }),
          direction,
          depth: String(depth),
        })
        router.replace(`/lineage?${urlParams}`, { scroll: false })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch lineage')
        setGraph(null)
      } finally {
        setLoading(false)
      }
    }

    fetchLineage()
  }, [selectedTable, direction, depth, confidenceThreshold, filters, viewMode, selectedColumn, router])

  // Get node details when node is selected
  const { data: nodeDetails } = useQuery<NodeDetailsResponse>({
    queryKey: ['node-details', selectedNodeId],
    queryFn: () => getNodeDetails(selectedNodeId!),
    enabled: !!selectedNodeId,
  })

  // Get available tables for filters
  const { data: allTables } = useQuery<TableInfoResponse[]>({
    queryKey: ['all-tables'],
    queryFn: () => getAllTables(100),
  })

  const handleTableSelect = (table: TableInfoResponse) => {
    setSelectedTable(table)
    setSelectedNodeId(null)
    setShowNodeDetails(false)
  }

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setShowNodeDetails(true)
  }

  const handleExport = () => {
    if (graph) {
      const dataStr = JSON.stringify(graph, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `lineage-${selectedTable?.table}-${Date.now()}.json`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  // Extract unique values for filters
  const availableSchemas = Array.from(new Set(allTables?.map(t => t.schema).filter(Boolean) || []))
  const availableDatabases = Array.from(new Set(allTables?.map(t => t.database).filter(Boolean) || []))

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-surface-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <GitBranch className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Data Lineage</h1>
              <p className="text-sm text-slate-400">
                Visualize and explore data lineage relationships
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {graph && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                icon={<Download className="w-4 h-4" />}
              >
                Export
              </Button>
            )}
            {selectedTable && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowImpactPanel(!showImpactPanel)}
              >
                {showImpactPanel ? 'Hide' : 'Show'} Impact
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex min-h-0">
        {/* Left Sidebar - Controls */}
        <div className="w-80 flex-shrink-0 bg-surface-900/50 border-r border-surface-700/50 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Table Search */}
            <div className="glass-card p-4">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Select Table
              </label>
              <LineageSearch
                onTableSelect={handleTableSelect}
                selectedTable={selectedTable}
              />
            </div>

            {/* Column Lineage View Toggle */}
            {selectedTable && (
              <ColumnLineageView
                table={selectedTable.table}
                schema={selectedTable.schema}
                columns={[]}
                onGraphChange={(graph) => {
                  if (graph) {
                    setGraph(graph)
                  }
                }}
              />
            )}

            {/* Filters */}
            <LineageFilters
              filters={filters}
              onChange={setFilters}
              availableSchemas={availableSchemas}
              availableDatabases={availableDatabases}
            />

            {/* Basic Controls */}
            <div className="glass-card p-4 space-y-4">
              <h3 className="text-sm font-semibold text-white mb-3">Graph Settings</h3>
            
            {/* Direction */}
            <Select
              label="Direction"
              value={direction}
              onChange={(value) => setDirection(value as 'upstream' | 'downstream' | 'both')}
              options={[
                { value: 'both', label: 'Both' },
                { value: 'upstream', label: 'Upstream' },
                { value: 'downstream', label: 'Downstream' },
              ]}
            />

            {/* Depth */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Depth: {depth}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            {/* Confidence Threshold */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Min Confidence: {confidenceThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>0.0</span>
                <span>1.0</span>
              </div>
            </div>

            {/* Layout */}
            <Select
              label="Layout"
              value={layout}
              onChange={(value) => setLayout(value as 'hierarchical' | 'circular' | 'force-directed' | 'breadth-first' | 'grid')}
              options={[
                { value: 'hierarchical', label: 'Hierarchical' },
                { value: 'circular', label: 'Circular' },
                { value: 'force-directed', label: 'Force-Directed' },
                { value: 'breadth-first', label: 'Breadth-First' },
                { value: 'grid', label: 'Grid' },
              ]}
            />

              {/* Stats */}
              {graph && (
                <div className="pt-4 border-t border-surface-700/50">
                  <h3 className="text-sm font-semibold text-slate-300 mb-2">Graph Stats</h3>
                  <div className="space-y-1 text-sm text-slate-400">
                    <div className="flex justify-between">
                      <span>Nodes:</span>
                      <span className="font-mono text-white">{graph.nodes.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Edges:</span>
                      <span className="font-mono text-white">{graph.edges.length}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center - Graph Area */}
        <div className="flex-1 p-6 flex flex-col min-w-0">
          {loading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full border-2 border-accent-500/20 border-t-accent-500 animate-spin mx-auto mb-4" />
                <div className="text-slate-400">Loading lineage graph...</div>
              </div>
            </div>
          )}

          {error && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-danger-400 font-medium mb-2">Error</div>
                <div className="text-slate-400">{error}</div>
              </div>
            </div>
          )}

          {!loading && !error && !selectedTable && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
                  <GitBranch className="w-8 h-8 text-slate-600" />
                </div>
                <div className="text-slate-400 text-lg mb-2">No table selected</div>
                <div className="text-slate-500 text-sm">
                  Search and select a table to view its lineage
                </div>
              </div>
            </div>
          )}

          {!loading && !error && graph && (
            <div className="h-full flex flex-col">
              <div className="mb-4 glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-white">
                      Lineage Graph
                    </h2>
                    <p className="text-sm text-slate-400">
                      {graph.nodes.length} nodes, {graph.edges.length} relationships
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs text-slate-500">
                    <span>Zoom: Scroll wheel</span>
                    <span>•</span>
                    <span>Pan: Click & drag</span>
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-0 glass-card overflow-hidden">
                <EnhancedLineageViewer
                  graph={graph}
                  loading={loading}
                  layout={layout}
                  onNodeClick={handleNodeClick}
                />
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar - Impact Analysis & Node Details */}
        {(showImpactPanel || showNodeDetails) && (
          <div className="w-80 flex-shrink-0 bg-surface-900/50 border-l border-surface-700/50 p-4 overflow-y-auto space-y-4">
            {showImpactPanel && selectedTable && (
              <ImpactAnalysis
                table={selectedTable.table}
                schema={selectedTable.schema}
                isOpen={showImpactPanel}
                onClose={() => setShowImpactPanel(false)}
              />
            )}

            {showNodeDetails && nodeDetails && (
              <div className="glass-card p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Node Details</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowNodeDetails(false)
                      setSelectedNodeId(null)
                    }}
                  >
                    Close
                  </Button>
                </div>
                <div className="space-y-3 text-sm">
                  <div>
                    <div className="text-slate-500">Label</div>
                    <div className="font-medium text-white">{nodeDetails.label}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Type</div>
                    <div className="font-medium text-white capitalize">{nodeDetails.type}</div>
                  </div>
                  {nodeDetails.table && (
                    <div>
                      <div className="text-slate-500">Table</div>
                      <div className="font-medium text-white">{nodeDetails.table}</div>
                    </div>
                  )}
                  {nodeDetails.column && (
                    <div>
                      <div className="text-slate-500">Column</div>
                      <div className="font-medium text-white">{nodeDetails.column}</div>
                    </div>
                  )}
                  <div>
                    <div className="text-slate-500">Upstream Count</div>
                    <div className="font-medium text-white">{nodeDetails.upstream_count}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Downstream Count</div>
                    <div className="font-medium text-white">{nodeDetails.downstream_count}</div>
                  </div>
                  {nodeDetails.providers && nodeDetails.providers.length > 0 && (
                    <div>
                      <div className="text-slate-500">Providers</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {nodeDetails.providers.map((provider) => (
                          <span
                            key={provider}
                            className="px-2 py-1 text-xs bg-surface-700 text-slate-300 rounded"
                          >
                            {provider}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function LineagePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-full">
        <div className="w-10 h-10 rounded-full border-2 border-accent-500/20 border-t-accent-500 animate-spin" />
      </div>
    }>
      <LineageContent />
    </Suspense>
  )
}
