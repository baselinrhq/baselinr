'use client'

import { DatasetValidationConfig } from '@/types/config'

export interface DatasetValidationSectionProps {
  config?: DatasetValidationConfig | null
  onChange: (config: DatasetValidationConfig) => void
}

export function DatasetValidationSection({}: DatasetValidationSectionProps) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Validation Configuration</h3>
        <p className="text-sm text-slate-400">
          Configure validation rules for this dataset. Column-specific rules should be configured in the Columns tab.
        </p>
      </div>

      <div className="text-sm text-slate-400">
        Table-level validation rules configuration will be implemented here.
      </div>
    </div>
  )
}

