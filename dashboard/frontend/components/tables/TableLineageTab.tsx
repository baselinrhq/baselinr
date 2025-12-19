'use client'

import { useState } from 'react'
import { GitBranch, ArrowUp, ArrowDown, Search, Maximize2 } from 'lucide-react'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
import { Select } from '@/components/ui/Select'
import LineageMiniGraph from '@/components/lineage/LineageMiniGraph'
import Link from 'next/link'

interface TableLineageTabProps {
  tableName: string
  schema?: string
}

export default function TableLineageTab({
  tableName,
  schema
}: TableLineageTabProps) {
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both')
  const [depth, setDepth] = useState(2)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="glass-card p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Direction Toggle */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Direction
            </label>
            <div className="flex gap-2">
              <Button
                variant={direction === 'upstream' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setDirection('upstream')}
              >
                <ArrowUp className="w-4 h-4 mr-1" />
                Upstream
              </Button>
              <Button
                variant={direction === 'downstream' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setDirection('downstream')}
              >
                <ArrowDown className="w-4 h-4 mr-1" />
                Downstream
              </Button>
              <Button
                variant={direction === 'both' ? 'primary' : 'outline'}
                size="sm"
                onClick={() => setDirection('both')}
              >
                <GitBranch className="w-4 h-4 mr-1" />
                Both
              </Button>
            </div>
          </div>

          {/* Depth Control */}
          <div>
            <Select
              label="Depth"
              value={depth.toString()}
              onChange={(value) => setDepth(Number(value))}
              options={[
                { value: '1', label: '1 Level' },
                { value: '2', label: '2 Levels' },
                { value: '3', label: '3 Levels' },
                { value: '4', label: '4 Levels' },
                { value: '5', label: '5 Levels' },
              ]}
            />
          </div>

          {/* Search */}
          <div className="md:col-span-2">
            <Input
              label="Search Tables"
              placeholder="Search within lineage..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
            />
          </div>
        </div>

        {/* Expand to Full Lineage */}
        <div className="mt-4 pt-4 border-t border-surface-700/50">
          <Link href={`/lineage?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
            <Button
              variant="outline"
              icon={<Maximize2 className="w-4 h-4" />}
              iconPosition="left"
            >
              Expand to Full Lineage View
            </Button>
          </Link>
        </div>
      </div>

      {/* Lineage Graph */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Data Lineage</h2>
        <div className="border border-surface-700/50 rounded-lg p-4 bg-surface-800/30 min-h-[400px]">
          <LineageMiniGraph
            table={tableName}
            schema={schema}
            direction={direction}
          />
        </div>
      </div>
    </div>
  )
}

