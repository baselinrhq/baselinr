'use client'

import { useState } from 'react'
import { GitBranch, ArrowUp, ArrowDown, Search, Maximize2 } from 'lucide-react'
import { Button } from '@/components/ui'
import { Input } from '@/components/ui'
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
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Direction Toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Depth
            </label>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value={1}>1 Level</option>
              <option value={2}>2 Levels</option>
              <option value={3}>3 Levels</option>
              <option value={4}>4 Levels</option>
              <option value={5}>5 Levels</option>
            </select>
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
        <div className="mt-4 pt-4 border-t border-gray-200">
          <Button
            variant="outline"
            asChild
          >
            <Link href={`/lineage?table=${encodeURIComponent(tableName)}${schema ? `&schema=${encodeURIComponent(schema)}` : ''}`}>
              <Maximize2 className="w-4 h-4 mr-2" />
              Expand to Full Lineage View
            </Link>
          </Button>
        </div>
      </div>

      {/* Lineage Graph */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Data Lineage</h2>
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 min-h-[400px]">
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

