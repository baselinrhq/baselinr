'use client'

/**
 * Enhanced lineage exploration interface
 */

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { getLineageGraph, getNodeDetails, getAllTables } from '@/lib/api/lineage'
import { getLineageGraphWithFilters } from '@/lib/api/lineage'
import type { LineageGraphResponse, TableInfoResponse, LineageFilters, NodeDetailsResponse } from '@/types/lineage'
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
  const [filters, setFilters] = useState<LineageFilters>({})
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Lineage Explorer</h1>
            <p className="text-sm text-gray-600 mt-1">
              Visualize and explore data lineage relationships
            </p>
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
      <div className="flex h-[calc(100vh-120px)]">
        {/* Left Sidebar - Controls */}
        <div className="w-80 bg-white border-r border-gray-200 p-6 overflow-y-auto space-y-4">
          {/* Table Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
              columns={[]} // TODO: Fetch columns from API
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
          <div className="space-y-4 pt-4 border-t border-gray-200">
            {/* Direction */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Direction
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as 'upstream' | 'downstream' | 'both')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="both">Both</option>
                <option value="upstream">Upstream</option>
                <option value="downstream">Downstream</option>
              </select>
            </div>

            {/* Depth */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Depth: {depth}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            {/* Confidence Threshold */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Min Confidence: {confidenceThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.0</span>
                <span>1.0</span>
              </div>
            </div>

            {/* Layout */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Layout
              </label>
              <select
                value={layout}
                onChange={(e) => setLayout(e.target.value as 'hierarchical' | 'circular' | 'force-directed' | 'breadth-first' | 'grid')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="hierarchical">Hierarchical</option>
                <option value="circular">Circular</option>
                <option value="force-directed">Force-Directed</option>
                <option value="breadth-first">Breadth-First</option>
                <option value="grid">Grid</option>
              </select>
            </div>

            {/* Stats */}
            {graph && (
              <div className="pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Graph Stats</h3>
                <div className="space-y-1 text-sm text-gray-600">
                  <div>Nodes: {graph.nodes.length}</div>
                  <div>Edges: {graph.edges.length}</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Center - Graph Area */}
        <div className="flex-1 p-6 flex flex-col min-w-0">
          {loading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <div className="text-gray-500">Loading lineage graph...</div>
              </div>
            </div>
          )}

          {error && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-red-600 font-medium mb-2">Error</div>
                <div className="text-gray-600">{error}</div>
              </div>
            </div>
          )}

          {!loading && !error && !selectedTable && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-gray-400 text-lg mb-2">No table selected</div>
                <div className="text-gray-500 text-sm">
                  Search and select a table to view its lineage
                </div>
              </div>
            </div>
          )}

          {!loading && !error && graph && (
            <div className="h-full flex flex-col">
              <div className="mb-4 bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      Lineage Graph
                    </h2>
                    <p className="text-sm text-gray-600">
                      {graph.nodes.length} nodes, {graph.edges.length} relationships
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs text-gray-500">
                    <span>Zoom: Scroll wheel</span>
                    <span>•</span>
                    <span>Pan: Click & drag</span>
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-0">
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
          <div className="w-80 bg-white border-l border-gray-200 p-6 overflow-y-auto space-y-4">
            {showImpactPanel && selectedTable && (
              <ImpactAnalysis
                table={selectedTable.table}
                schema={selectedTable.schema}
                isOpen={showImpactPanel}
                onClose={() => setShowImpactPanel(false)}
              />
            )}

            {showNodeDetails && nodeDetails && (
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Node Details</h3>
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
                    <div className="text-gray-500">Label</div>
                    <div className="font-medium text-gray-900">{nodeDetails.label}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Type</div>
                    <div className="font-medium text-gray-900 capitalize">{nodeDetails.type}</div>
                  </div>
                  {nodeDetails.table && (
                    <div>
                      <div className="text-gray-500">Table</div>
                      <div className="font-medium text-gray-900">{nodeDetails.table}</div>
                    </div>
                  )}
                  {nodeDetails.column && (
                    <div>
                      <div className="text-gray-500">Column</div>
                      <div className="font-medium text-gray-900">{nodeDetails.column}</div>
                    </div>
                  )}
                  <div>
                    <div className="text-gray-500">Upstream Count</div>
                    <div className="font-medium text-gray-900">{nodeDetails.upstream_count}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Downstream Count</div>
                    <div className="font-medium text-gray-900">{nodeDetails.downstream_count}</div>
                  </div>
                  {nodeDetails.providers && nodeDetails.providers.length > 0 && (
                    <div>
                      <div className="text-gray-500">Providers</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {nodeDetails.providers.map((provider) => (
                          <span
                            key={provider}
                            className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
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
    <Suspense fallback={<div>Loading...</div>}>
      <LineageContent />
    </Suspense>
  )
}
