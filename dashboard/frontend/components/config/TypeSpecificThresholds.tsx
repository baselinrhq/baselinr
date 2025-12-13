'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Toggle } from '@/components/ui/Toggle'
import { Tabs } from '@/components/ui/Tabs'
import { ThresholdConfig } from './ThresholdConfig'

export interface TypeSpecificThresholdsProps {
  enableTypeSpecificThresholds: boolean
  typeSpecificThresholds: Record<string, Record<string, Record<string, number>>>
  onChange: (enabled: boolean, thresholds?: Record<string, Record<string, Record<string, number>>>) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

type DataType = 'numeric' | 'categorical' | 'timestamp' | 'boolean'
type MetricType = 'mean' | 'stddev' | 'distinct_count' | 'distinct_percent' | 'default'

const DATA_TYPES: Array<{ id: DataType; label: string; description: string }> = [
  {
    id: 'numeric',
    label: 'Numeric',
    description: 'For numeric columns (int, float, decimal)',
  },
  {
    id: 'categorical',
    label: 'Categorical',
    description: 'For categorical columns (string, enum)',
  },
  {
    id: 'timestamp',
    label: 'Timestamp',
    description: 'For timestamp/date columns',
  },
  {
    id: 'boolean',
    label: 'Boolean',
    description: 'For boolean columns',
  },
]

const NUMERIC_METRICS: Array<{ id: MetricType; label: string }> = [
  { id: 'mean', label: 'Mean' },
  { id: 'stddev', label: 'Standard Deviation' },
  { id: 'default', label: 'Default (Other Metrics)' },
]

const CATEGORICAL_METRICS: Array<{ id: MetricType; label: string }> = [
  { id: 'distinct_count', label: 'Distinct Count' },
  { id: 'distinct_percent', label: 'Distinct Percent' },
  { id: 'default', label: 'Default (Other Metrics)' },
]

export function TypeSpecificThresholds({
  enableTypeSpecificThresholds,
  typeSpecificThresholds,
  onChange,
  errors,
  isLoading,
}: TypeSpecificThresholdsProps) {
  const [activeType, setActiveType] = useState<DataType>('numeric')

  const handleEnabledToggle = (enabled: boolean) => {
    onChange(enabled, enabled ? typeSpecificThresholds : undefined)
  }

  const handleThresholdChange = (type: DataType, metric: MetricType, thresholds: Record<string, number>) => {
    const newThresholds = {
      ...typeSpecificThresholds,
      [type]: {
        ...(typeSpecificThresholds[type] || {}),
        [metric]: thresholds,
      },
    }
    onChange(enableTypeSpecificThresholds, newThresholds)
  }

  const getCurrentThresholds = (type: DataType, metric: MetricType): Record<string, number> => {
    return (typeSpecificThresholds[type]?.[metric] as Record<string, number>) || {
      low: 5.0,
      medium: 15.0,
      high: 30.0,
    }
  }

  const getMetricsForType = (type: DataType): Array<{ id: MetricType; label: string }> => {
    switch (type) {
      case 'numeric':
        return NUMERIC_METRICS
      case 'categorical':
        return CATEGORICAL_METRICS
      case 'timestamp':
      case 'boolean':
        return [{ id: 'default', label: 'Default Thresholds' }]
      default:
        return []
    }
  }

  return (
    <Card>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-white mb-1">Type-Specific Thresholds</h4>
            <p className="text-xs text-slate-400">
              Adjust drift detection sensitivity based on column data type to reduce false positives
            </p>
          </div>
          <Toggle
            checked={enableTypeSpecificThresholds}
            onChange={handleEnabledToggle}
            disabled={isLoading}
          />
        </div>

        {enableTypeSpecificThresholds && (
          <div className="space-y-4">
            <Tabs
              activeTab={activeType}
              onChange={(tabId) => setActiveType(tabId as DataType)}
              tabs={DATA_TYPES.map((type) => ({
                id: type.id,
                label: type.label,
              }))}
            />

            <div className="space-y-4">
              {DATA_TYPES.find((t) => t.id === activeType) && (
                <div className="text-sm text-slate-400 mb-4">
                  {DATA_TYPES.find((t) => t.id === activeType)?.description}
                </div>
              )}

              {getMetricsForType(activeType).map((metric) => (
                <div key={metric.id} className="border border-surface-700/50 rounded-lg p-4">
                  <h5 className="text-sm font-medium text-white mb-4">{metric.label}</h5>
                  <ThresholdConfig
                    thresholds={getCurrentThresholds(activeType, metric.id)}
                    onChange={(thresholds) => handleThresholdChange(activeType, metric.id, thresholds)}
                    unit="%"
                    min={0}
                    max={100}
                    step={0.1}
                    errors={errors}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {!enableTypeSpecificThresholds && (
          <div className="glass-card border-surface-700/50 rounded-lg p-4 text-sm text-slate-400">
            Enable type-specific thresholds to configure different sensitivity levels for different data types.
          </div>
        )}
      </div>
    </Card>
  )
}

