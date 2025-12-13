'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import RecommendationCard from './RecommendationCard'
import type { TableRecommendation } from '@/types/recommendation'

interface RecommendationListProps {
  recommendations: TableRecommendation[]
  onApply: (tables: Array<{ schema: string; table: string; database?: string }>) => void
}

export default function RecommendationList({ recommendations, onApply }: RecommendationListProps) {
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<'confidence' | 'score' | 'table'>('confidence')
  const [filterConfidence, setFilterConfidence] = useState<number>(0)

  const handleToggleSelect = (schema: string, table: string) => {
    const key = `${schema}.${table}`
    const newSelected = new Set(selectedTables)
    if (newSelected.has(key)) {
      newSelected.delete(key)
    } else {
      newSelected.add(key)
    }
    setSelectedTables(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedTables.size === filteredRecommendations.length) {
      setSelectedTables(new Set())
    } else {
      const allKeys = new Set(
        filteredRecommendations.map((r) => `${r.schema}.${r.table}`)
      )
      setSelectedTables(allKeys)
    }
  }

  const handleApplySelected = () => {
    const tables = filteredRecommendations
      .filter((r) => selectedTables.has(`${r.schema}.${r.table}`))
      .map((r) => ({
        schema: r.schema,
        table: r.table,
        database: r.database || undefined,
      }))
    onApply(tables)
  }

  // Filter and sort recommendations
  const filteredRecommendations = recommendations
    .filter((r) => r.confidence >= filterConfidence)
    .sort((a, b) => {
      if (sortBy === 'confidence') {
        return b.confidence - a.confidence
      } else if (sortBy === 'score') {
        return b.score - a.score
      } else {
        const aName = `${a.schema}.${a.table}`
        const bName = `${b.schema}.${b.table}`
        return aName.localeCompare(bName)
      }
    })

  if (recommendations.length === 0) {
    return (
      <Card>
        <CardBody>
          <div className="text-center py-12">
            <p className="text-slate-400">No recommendations available</p>
          </div>
        </CardBody>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters and Actions */}
      <Card>
        <CardBody>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <Select
                label="Sort by"
                value={sortBy}
                onChange={(value) => setSortBy(value as 'confidence' | 'score' | 'table')}
                options={[
                  { value: 'confidence', label: 'Confidence' },
                  { value: 'score', label: 'Score' },
                  { value: 'table', label: 'Table Name' },
                ]}
              />
              <Input
                label="Min Confidence"
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={filterConfidence.toString()}
                onChange={(e) => setFilterConfidence(parseFloat(e.target.value) || 0)}
                className="w-24"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleSelectAll}
                variant="secondary"
                size="sm"
              >
                {selectedTables.size === filteredRecommendations.length ? 'Deselect All' : 'Select All'}
              </Button>
              {selectedTables.size > 0 && (
                <Button
                  onClick={handleApplySelected}
                  variant="primary"
                  size="sm"
                >
                  Apply Selected ({selectedTables.size})
                </Button>
              )}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Recommendations */}
      <div className="space-y-4">
        {filteredRecommendations.map((recommendation) => {
          const key = `${recommendation.schema}.${recommendation.table}`
          const isSelected = selectedTables.has(key)
          return (
            <RecommendationCard
              key={key}
              recommendation={recommendation}
              isSelected={isSelected}
              onSelect={() => handleToggleSelect(recommendation.schema, recommendation.table)}
              onApply={() => onApply([{
                schema: recommendation.schema,
                table: recommendation.table,
                database: recommendation.database || undefined,
              }])}
            />
          )
        })}
      </div>

      {filteredRecommendations.length === 0 && (
        <Card>
          <CardBody>
            <div className="text-center py-12">
              <p className="text-slate-400">No recommendations match the current filters</p>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

