'use client'

import { useState } from 'react'
import { Columns, Table2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { getColumnLineageGraph } from '@/lib/api/lineage'
import type { LineageGraphResponse } from '@/types/lineage'

interface ColumnLineageViewProps {
  table: string
  schema?: string
  columns?: string[]
  onGraphChange?: (graph: LineageGraphResponse) => void
}

export default function ColumnLineageView({
  table,
  schema,
  columns = [],
  onGraphChange,
}: ColumnLineageViewProps) {
  const [viewMode, setViewMode] = useState<'table' | 'column'>('table')
  const [selectedColumn, setSelectedColumn] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [columnGraph, setColumnGraph] = useState<LineageGraphResponse | null>(null)

  const handleViewModeChange = (mode: 'table' | 'column') => {
    setViewMode(mode)
    if (mode === 'table' && onGraphChange) {
      onGraphChange(null as unknown as LineageGraphResponse) // Reset to table view
    }
  }

  const handleColumnSelect = async (column: string) => {
    setSelectedColumn(column)
    if (!column) {
      setColumnGraph(null)
      if (onGraphChange) {
        onGraphChange(null as unknown as LineageGraphResponse)
      }
      return
    }

    setIsLoading(true)
    try {
      const graph = await getColumnLineageGraph({
        table,
        schema,
        column,
        direction: 'both',
        depth: 3,
      })
      setColumnGraph(graph)
      if (onGraphChange) {
        onGraphChange(graph)
      }
    } catch (err) {
      console.error('Failed to load column lineage:', err)
      setColumnGraph(null)
    } finally {
      setIsLoading(false)
    }
  }

  if (!table) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Lineage View</h3>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'table' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => handleViewModeChange('table')}
            icon={<Table2 className="w-4 h-4" />}
          >
            Table
          </Button>
          <Button
            variant={viewMode === 'column' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => handleViewModeChange('column')}
            icon={<Columns className="w-4 h-4" />}
          >
            Column
          </Button>
        </div>
      </CardHeader>
      <CardBody>
        {viewMode === 'column' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Column
              </label>
              <Select
                value={selectedColumn}
                onChange={(value) => handleColumnSelect(value)}
                options={[
                  { value: '', label: 'Select a column...' },
                  ...columns.map(col => ({ value: col, label: col })),
                ]}
              />
            </div>

            {isLoading && (
              <div className="text-center py-4 text-gray-500">
                Loading column lineage...
              </div>
            )}

            {columnGraph && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-blue-900">
                  <div className="font-medium mb-1">Column Lineage Loaded</div>
                  <div className="text-xs text-blue-700">
                    {columnGraph.nodes.length} nodes, {columnGraph.edges.length} relationships
                  </div>
                </div>
              </div>
            )}

            {!selectedColumn && (
              <div className="text-center py-8 text-gray-500">
                <Columns className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p>Select a column to view column-level lineage</p>
              </div>
            )}
          </div>
        )}

        {viewMode === 'table' && (
          <div className="text-center py-4 text-gray-500 text-sm">
            Table-level lineage view is active
          </div>
        )}
      </CardBody>
    </Card>
  )
}

