'use client'

import { useParams, useSearchParams } from 'next/navigation'
import { Database } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabPanel } from '@/components/ui'
import { LoadingSpinner } from '@/components/ui'
import TableOverviewTab from '@/components/tables/TableOverviewTab'
import TableDriftTab from '@/components/tables/TableDriftTab'
import TableValidationTab from '@/components/tables/TableValidationTab'
import TableLineageTab from '@/components/tables/TableLineageTab'
import TableConfigTab from '@/components/tables/TableConfigTab'
import QualityScoreCard from '@/components/quality/QualityScoreCard'
import { fetchTableScore } from '@/lib/api'
import { useState } from 'react'

export default function TableMetricsClient() {
  const params = useParams()
  const searchParams = useSearchParams()
  const tableName = params?.tableName ? decodeURIComponent(String(params.tableName)) : ''
  const schema = searchParams.get('schema') || undefined
  const warehouse = searchParams.get('warehouse') || undefined

  const isPlaceholder = tableName === '__placeholder__'

  const [activeTab, setActiveTab] = useState('overview')

  // Fetch quality score
  const {
    data: qualityScore,
    isLoading: isLoadingScore,
    error: scoreError,
  } = useQuery({
    queryKey: ['quality-score', tableName, schema || null],
    queryFn: async () => {
      try {
        console.log(`[Quality Score] Fetching score for table: ${tableName}, schema: ${schema || 'none'}`)
        const score = await fetchTableScore(tableName, schema)
        console.log(`[Quality Score] Successfully fetched score:`, score)
        return score
      } catch (error) {
        // Log error for debugging
        console.error(`[Quality Score] Error fetching score for ${tableName} (schema: ${schema || 'none'}):`, error)
        throw error
      }
    },
    staleTime: 30000,
    retry: (failureCount, error) => {
      // Don't retry on 404 (score doesn't exist), but retry on other errors
      if (error instanceof Error && error.message.includes('404')) {
        console.log(`[Quality Score] 404 error - score not found, not retrying`)
        return false
      }
      console.log(`[Quality Score] Retrying (attempt ${failureCount + 1})`)
      return failureCount < 2
    },
    enabled: !!tableName && !isPlaceholder,
  })

  // Handle placeholder route used for static export
  if (isPlaceholder) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-400">Loading...</div>
      </div>
    )
  }

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <Database className="w-4 h-4" />
    },
    {
      id: 'drift',
      label: 'Drift',
      icon: <Database className="w-4 h-4" />
    },
    {
      id: 'validation',
      label: 'Validation',
      icon: <Database className="w-4 h-4" />
    },
    {
      id: 'lineage',
      label: 'Lineage',
      icon: <Database className="w-4 h-4" />
    },
    {
      id: 'config',
      label: 'Configuration',
      icon: <Database className="w-4 h-4" />
    }
  ]

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white flex items-center gap-2">
          <Database className="w-8 h-8 text-cyan-400" />
          {tableName}
        </h1>
        {schema && (
          <p className="text-slate-400 mt-1">
            Schema: {schema}
          </p>
        )}
      </div>

      {/* Quality Score Card */}
      {isLoadingScore ? (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" />
        </div>
      ) : scoreError ? (
        <div className="bg-surface-800/40 border border-surface-700/50 rounded-xl p-4 text-center">
          <p className="text-sm text-slate-400">
            {scoreError instanceof Error && scoreError.message.includes('404')
              ? 'Quality score not available for this table'
              : 'Error loading quality score'}
          </p>
        </div>
      ) : qualityScore ? (
        <QualityScoreCard score={qualityScore} />
      ) : (
        <div className="bg-surface-800/40 border border-surface-700/50 rounded-xl p-4 text-center">
          <p className="text-sm text-slate-400">Quality score not available for this table</p>
        </div>
      )}

      {/* Tabs */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="px-6 pt-6">
          <Tabs
            tabs={tabs}
            activeTab={activeTab}
            onChange={setActiveTab}
          />
        </div>

        <div className="px-6 pb-6">
          <TabPanel tabId="overview" activeTab={activeTab}>
            <TableOverviewTab
              tableName={tableName}
              schema={schema}
              warehouse={warehouse}
            />
          </TabPanel>

          <TabPanel tabId="drift" activeTab={activeTab}>
            <TableDriftTab
              tableName={tableName}
              schema={schema}
              warehouse={warehouse}
            />
          </TabPanel>

          <TabPanel tabId="validation" activeTab={activeTab}>
            <TableValidationTab
              tableName={tableName}
              schema={schema}
            />
          </TabPanel>

          <TabPanel tabId="lineage" activeTab={activeTab}>
            <TableLineageTab
              tableName={tableName}
              schema={schema}
            />
          </TabPanel>

          <TabPanel tabId="config" activeTab={activeTab}>
            <TableConfigTab
              tableName={tableName}
              schema={schema}
            />
          </TabPanel>
        </div>
      </div>
    </div>
  )
}
