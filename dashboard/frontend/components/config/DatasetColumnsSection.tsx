'use client'

import { ColumnConfig } from '@/types/config'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Plus } from 'lucide-react'

export interface DatasetColumnsSectionProps {
  columns?: ColumnConfig[] | null
  onChange: (columns: ColumnConfig[]) => void
}

export function DatasetColumnsSection({ columns }: DatasetColumnsSectionProps) {
  const columnList = columns || []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Column Configuration</h3>
        <p className="text-sm text-slate-400">
          Configure profiling, drift, validation, and anomaly detection for specific columns
        </p>
      </div>

      {columnList.length > 0 ? (
        <div className="space-y-4">
          {columnList.map((column, index) => (
            <Card key={index} padding="sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">{column.name}</div>
                  <div className="text-sm text-slate-400">
                    {column.profiling && 'Profiling '}
                    {column.drift && 'Drift '}
                    {column.anomaly && 'Anomaly '}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-slate-400">
          <p className="mb-4">No column configurations yet</p>
          <Button variant="outline" icon={<Plus className="w-4 h-4" />}>
            Add Column Configuration
          </Button>
        </div>
      )}
    </div>
  )
}

