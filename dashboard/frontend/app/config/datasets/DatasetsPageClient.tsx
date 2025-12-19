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
  const {
    currentConfig,
    loadConfig,
    updateConfigPath,
    saveConfig,
    isLoading: isConfigLoading,
    error: configError,
    canSave,
  } = useConfig()

  const [saveSuccess, setSaveSuccess] = useState(false)
  const [tableErrors, setTableErrors] = useState<Record<string, string>>({})
  const [hasTriedLoad, setHasTriedLoad] = useState(false)

  // Load config on mount
  useEffect(() => {
    if (!currentConfig && !hasTriedLoad && !configError) {
      setHasTriedLoad(true)
      loadConfig().catch(() => {
        // Error is handled by useConfig hook
      })
    }
  }, [currentConfig, loadConfig, hasTriedLoad, configError])

  // Get current profiling config
  const tables: TablePattern[] = currentConfig?.profiling?.tables || []
  const discoveryOptions: DiscoveryOptionsConfig | undefined =
    currentConfig?.profiling?.discovery_options

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      setSaveSuccess(false)
      setTableErrors({})
      await saveConfig()
    },
    onSuccess: () => {
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
    onError: (error) => {
      if (error instanceof Error && error.message.includes('validation')) {
        setTableErrors({
          general: error.message,
        })
      } else {
        setTableErrors({
          general: error instanceof Error ? error.message : 'Failed to save configuration',
        })
      }
    },
  })

  const handleTablesChange = (newTables: TablePattern[]) => {
    updateConfigPath(['profiling', 'tables'], newTables)
  }

  const handleDiscoveryChange = (options: DiscoveryOptionsConfig) => {
    updateConfigPath(['profiling', 'discovery_options'], options)
  }

  const handleSave = () => {
    saveMutation.mutate()
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">Datasets & Tables</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Database className="w-6 h-6" />
            Datasets & Table Selection
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Select which tables to profile and configure how to profile, validate, and detect drift for each dataset
          </p>
        </div>
        {activeTab === 'tables' && (
          <div className="flex items-center gap-3">
            {saveSuccess && (
              <div className="flex items-center gap-2 text-sm text-emerald-400">
                <CheckCircle className="w-4 h-4" />
                <span>Saved successfully</span>
              </div>
            )}
            {tableErrors.general && (
              <div className="flex items-center gap-2 text-sm text-rose-400">
                <AlertCircle className="w-4 h-4" />
                <span>{tableErrors.general}</span>
              </div>
            )}
            <Button
              onClick={handleSave}
              disabled={!canSave || saveMutation.isPending}
              loading={saveMutation.isPending}
              icon={<Save className="w-4 h-4" />}
            >
              Save Configuration
            </Button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Card padding="none">
        <Tabs
          tabs={[
            { id: 'datasets', label: 'Dataset Configurations', icon: <Layers className="w-4 h-4" /> },
            { id: 'tables', label: 'Table Selection', icon: <Table className="w-4 h-4" /> },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        >
          {(currentTab) => (
            <>
              {currentTab === 'datasets' && (
                <div className="p-6">
                  <DatasetList onCreateNew={() => setIsWizardOpen(true)} />
                </div>
              )}

              {currentTab === 'tables' && (
                <div className="p-6 space-y-6">
                  {/* Main Content - Two Column Layout */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Table Selection - Left Column (2/3 width) */}
                    <div className="lg:col-span-2">
                      <TableSelection
                        tables={tables}
                        onChange={handleTablesChange}
                        errors={tableErrors}
                        isLoading={isConfigLoading || saveMutation.isPending}
                      />
                    </div>

                    {/* Discovery Settings - Right Column (1/3 width) */}
                    <div className="lg:col-span-1">
                      <TableDiscovery
                        discoveryOptions={discoveryOptions || {}}
                        onChange={handleDiscoveryChange}
                        errors={tableErrors}
                        isLoading={isConfigLoading || saveMutation.isPending}
                      />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </Tabs>
      </Card>

      {/* Create Dataset Wizard */}
      <DatasetWizard
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onSuccess={() => {
          setIsWizardOpen(false)
          // Refetch will be handled by DatasetList's query
        }}
      />
    </div>
  )
}
