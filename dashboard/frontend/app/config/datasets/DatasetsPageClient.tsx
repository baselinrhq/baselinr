'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { Database, ChevronRight, Table, Layers } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Tabs } from '@/components/ui/Tabs'
import { DatasetList } from '@/components/config/DatasetList'
import { DatasetWizard } from '@/components/config/DatasetWizard'
import { TableSelection } from '@/components/config/TableSelection'
import { TableDiscovery } from '@/components/config/TableDiscovery'
import { useConfig } from '@/hooks/useConfig'
import { TablePattern, DiscoveryOptionsConfig } from '@/types/config'
import { Save, CheckCircle, AlertCircle } from 'lucide-react'

export default function DatasetsPageClient() {
  const searchParams = useSearchParams()
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('datasets')

  // Set initial tab from URL param
  useEffect(() => {
    const tab = searchParams?.get('tab')
    if (tab === 'tables') {
      setActiveTab('tables')
    }
  }, [searchParams])

  const { currentConfig, updateConfigPath, saveConfig, isLoading: isConfigLoading, error: configError } = useConfig()

  const datasets = currentConfig?.datasets || []
  const tablePatterns = currentConfig?.table_patterns || []
  const discoveryOptions = currentConfig?.discovery_options || {}

  const saveMutation = useMutation({
    mutationFn: saveConfig,
    onSuccess: () => {
      // Success handled by useConfig hook
    },
  })

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync()
    } catch {
      // Error handled by mutation
    }
  }

  const handleAddDataset = () => {
    setIsWizardOpen(true)
  }

  const handleDatasetWizardComplete = (datasetConfig: {
    database?: string
    schema?: string
    table?: string
    connection_id?: string
  }) => {
    const newDataset = {
      database: datasetConfig.database || '',
      schema: datasetConfig.schema,
      table: datasetConfig.table || '',
      connection_id: datasetConfig.connection_id,
    }

    const existingDatasets = datasets || []
    updateConfigPath(['datasets'], [...existingDatasets, newDataset])
    setIsWizardOpen(false)
  }

  const handleRemoveDataset = (index: number) => {
    const updatedDatasets = datasets.filter((_: unknown, i: number) => i !== index)
    updateConfigPath(['datasets'], updatedDatasets)
  }

  const handleUpdateDataset = (index: number, updates: Partial<TablePattern>) => {
    const updatedDatasets = [...datasets]
    updatedDatasets[index] = { ...updatedDatasets[index], ...updates }
    updateConfigPath(['datasets'], updatedDatasets)
  }

  const handleAddTablePattern = (pattern: TablePattern) => {
    const existingPatterns = tablePatterns || []
    updateConfigPath(['table_patterns'], [...existingPatterns, pattern])
  }

  const handleRemoveTablePattern = (index: number) => {
    const updatedPatterns = tablePatterns.filter((_: unknown, i: number) => i !== index)
    updateConfigPath(['table_patterns'], updatedPatterns)
  }

  const handleUpdateTablePattern = (index: number, updates: Partial<TablePattern>) => {
    const updatedPatterns = [...tablePatterns]
    updatedPatterns[index] = { ...updatedPatterns[index], ...updates }
    updateConfigPath(['table_patterns'], updatedPatterns)
  }

  const handleUpdateDiscoveryOptions = (options: DiscoveryOptionsConfig) => {
    updateConfigPath(['discovery_options'], options)
  }

  const tabs = [
    { id: 'datasets', label: 'Datasets', icon: <Database className="w-4 h-4" /> },
    { id: 'tables', label: 'Table Patterns', icon: <Table className="w-4 h-4" /> },
    { id: 'discovery', label: 'Discovery', icon: <Layers className="w-4 h-4" /> },
  ]

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <Link href="/config" className="hover:text-cyan-400">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-white font-medium">Datasets</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Database className="w-6 h-6" />
              Dataset Configuration
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Configure which datasets and tables to profile
            </p>
          </div>
          <div className="flex items-center gap-3">
            {saveMutation.isSuccess && (
              <div className="flex items-center gap-2 text-success-400">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm">Saved</span>
              </div>
            )}
            {saveMutation.isError && (
              <div className="flex items-center gap-2 text-rose-400">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">Error saving</span>
              </div>
            )}
            <Button
              onClick={handleSave}
              disabled={saveMutation.isPending || isConfigLoading}
              icon={<Save className="w-4 h-4" />}
            >
              {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {configError && !currentConfig && (
        <Card className="border-rose-500/30 bg-rose-500/10 p-4">
          <div className="flex items-center gap-2 text-rose-300">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{configError}</span>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <div className="px-6 pt-6">
          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
        </div>

        <div className="px-6 pb-6 mt-6">
          {activeTab === 'datasets' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-white">Configured Datasets</h3>
                <Button onClick={handleAddDataset} variant="primary" size="sm">
                  Add Dataset
                </Button>
              </div>
              <DatasetList
                datasets={datasets}
                onRemove={handleRemoveDataset}
                onUpdate={handleUpdateDataset}
              />
            </div>
          )}

          {activeTab === 'tables' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-white">Table Patterns</h3>
                <Button
                  onClick={() => setActiveTab('discovery')}
                  variant="secondary"
                  size="sm"
                >
                  Use Discovery
                </Button>
              </div>
              <TableSelection
                patterns={tablePatterns}
                onAdd={handleAddTablePattern}
                onRemove={handleRemoveTablePattern}
                onUpdate={handleUpdateTablePattern}
              />
            </div>
          )}

          {activeTab === 'discovery' && (
            <TableDiscovery
              options={discoveryOptions}
              onUpdate={handleUpdateDiscoveryOptions}
            />
          )}
        </div>
      </Card>

      {/* Dataset Wizard Modal */}
      {isWizardOpen && (
        <DatasetWizard
          isOpen={isWizardOpen}
          onClose={() => setIsWizardOpen(false)}
          onComplete={handleDatasetWizardComplete}
        />
      )}
    </div>
  )
}
