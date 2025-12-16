'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, BarChart3, TrendingUp, Shield, AlertTriangle, Columns, FileText } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tabs } from '@/components/ui/Tabs'
import { DatasetConfigResponse } from '@/types/config'
import { updateDataset } from '@/lib/api/datasets'
import { DatasetProfilingSection } from './DatasetProfilingSection'
import { DatasetDriftSection } from './DatasetDriftSection'
import { DatasetValidationSection } from './DatasetValidationSection'
import { DatasetAnomalySection } from './DatasetAnomalySection'
import { DatasetColumnsSection } from './DatasetColumnsSection'

export interface DatasetDetailProps {
  dataset: DatasetConfigResponse
}

export function DatasetDetail({ dataset }: DatasetDetailProps) {
  const [activeTab, setActiveTab] = useState('profiling')
  const [config, setConfig] = useState(dataset.config)
  const queryClient = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: (updatedConfig: typeof config) =>
      updateDataset(dataset.dataset_id, { config: updatedConfig }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', dataset.dataset_id] })
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
    },
  })

  const handleConfigChange = (updates: Partial<typeof config>) => {
    setConfig({ ...config, ...updates })
  }

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync(config)
    } catch (error) {
      console.error('Failed to save dataset:', error)
    }
  }

  const tabs = [
    { id: 'profiling', label: 'Profiling', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'drift', label: 'Drift', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'validation', label: 'Validation', icon: <Shield className="w-4 h-4" /> },
    { id: 'anomaly', label: 'Anomaly', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'columns', label: 'Columns', icon: <Columns className="w-4 h-4" /> },
  ]

  return (
    <div className="space-y-6">
      {/* Source Info */}
      {dataset.source_file && (
        <Card>
          <div className="p-4 flex items-center gap-2 text-sm text-slate-400">
            <FileText className="w-4 h-4" />
            <span>Source file: {dataset.source_file}</span>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Card padding="none">
        <Tabs
          tabs={tabs}
          activeTab={activeTab}
          onChange={setActiveTab}
        >
          {(currentTab) => (
            <>
              {currentTab === 'profiling' && (
                <DatasetProfilingSection
                  config={config.profiling}
                  onChange={(profiling) => handleConfigChange({ profiling })}
                />
              )}

              {currentTab === 'drift' && (
                <DatasetDriftSection
                  config={config.drift}
                  onChange={(drift) => handleConfigChange({ drift })}
                />
              )}

              {currentTab === 'validation' && (
                <DatasetValidationSection
                  config={config.validation}
                  onChange={(validation) => handleConfigChange({ validation })}
                />
              )}

              {currentTab === 'anomaly' && (
                <DatasetAnomalySection
                  config={config.anomaly}
                  onChange={(anomaly) => handleConfigChange({ anomaly })}
                />
              )}

              {currentTab === 'columns' && (
                <DatasetColumnsSection
                  columns={config.columns}
                  onChange={(columns) => handleConfigChange({ columns })}
                />
              )}
            </>
          )}
        </Tabs>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          disabled={updateMutation.isPending}
          loading={updateMutation.isPending}
          icon={<Save className="w-4 h-4" />}
        >
          Save Changes
        </Button>
      </div>
    </div>
  )
}

