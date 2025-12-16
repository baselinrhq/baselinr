'use client'

import { DatasetAnomalyConfig } from '@/types/config'

export interface DatasetAnomalySectionProps {
  config?: DatasetAnomalyConfig | null
  onChange: (config: DatasetAnomalyConfig) => void
}

export function DatasetAnomalySection({}: DatasetAnomalySectionProps) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-medium text-white mb-2">Anomaly Detection Configuration</h3>
        <p className="text-sm text-slate-400">
          Column-level anomaly detection should be configured in the Columns tab.
        </p>
      </div>

      <div className="text-sm text-slate-400">
        Dataset-level anomaly configuration will be implemented here.
      </div>
    </div>
  )
}

