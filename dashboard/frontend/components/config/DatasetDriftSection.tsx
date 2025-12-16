'use client'

import { DatasetDriftConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Select } from '@/components/ui/Select'

export interface DatasetDriftSectionProps {
  config?: DatasetDriftConfig | null
  onChange: (config: DatasetDriftConfig) => void
}

export function DatasetDriftSection({ config, onChange }: DatasetDriftSectionProps) {
  const drift = config || {}

  const handleChange = (updates: Partial<DatasetDriftConfig>) => {
    onChange({ ...drift, ...updates })
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Drift Detection Configuration</h3>
        <p className="text-sm text-slate-400">
          Configure drift detection settings for this dataset
        </p>
      </div>

      <FormField label="Strategy">
        <Select
          value={drift.strategy || ''}
          onChange={(e) => {
            const strategy = e.target.value as 'absolute_threshold' | 'standard_deviation' | 'statistical' | ''
            handleChange({ strategy: strategy || null })
          }}
          options={[
            { value: '', label: 'Use global default' },
            { value: 'absolute_threshold', label: 'Absolute Threshold' },
            { value: 'standard_deviation', label: 'Standard Deviation' },
            { value: 'statistical', label: 'Statistical' },
          ]}
        />
      </FormField>

      {/* Thresholds would go here - simplified for now */}
    </div>
  )
}

