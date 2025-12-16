'use client'

import { DatasetProfilingConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { SamplingConfig } from './SamplingConfig'
import { PartitionConfig } from './PartitionConfig'

export interface DatasetProfilingSectionProps {
  config?: DatasetProfilingConfig | null
  onChange: (config: DatasetProfilingConfig) => void
}

export function DatasetProfilingSection({ config, onChange }: DatasetProfilingSectionProps) {
  const profiling = config || {}

  const handleChange = (updates: Partial<DatasetProfilingConfig>) => {
    onChange({ ...profiling, ...updates })
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Profiling Configuration</h3>
        <p className="text-sm text-slate-400">
          Configure profiling settings for this dataset
        </p>
      </div>

      {/* Partition */}
      {profiling.partition && (
        <PartitionConfig
          partition={profiling.partition}
          onChange={(partition) => handleChange({ partition })}
        />
      )}

      {/* Sampling */}
      {profiling.sampling && (
        <SamplingConfig
          sampling={profiling.sampling}
          onChange={(sampling) => handleChange({ sampling })}
        />
      )}

      {/* Metrics */}
      <FormField label="Metrics (comma-separated)">
        <Input
          value={profiling.metrics?.join(', ') || ''}
          onChange={(e) => {
            const metrics = e.target.value.split(',').map(m => m.trim()).filter(Boolean)
            handleChange({ metrics: metrics.length > 0 ? metrics : undefined })
          }}
          placeholder="count, null_count, distinct_count"
        />
      </FormField>
    </div>
  )
}

