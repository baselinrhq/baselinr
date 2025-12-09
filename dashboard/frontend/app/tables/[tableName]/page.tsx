'use client'

import { useParams, useSearchParams } from 'next/navigation'
import { Database } from 'lucide-react'
import { Tabs, TabPanel } from '@/components/ui'
import TableOverviewTab from '@/components/tables/TableOverviewTab'
import TableDriftTab from '@/components/tables/TableDriftTab'
import TableValidationTab from '@/components/tables/TableValidationTab'
import TableLineageTab from '@/components/tables/TableLineageTab'
import TableConfigTab from '@/components/tables/TableConfigTab'
import { useState } from 'react'

export default function TableMetricsPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const tableName = params.tableName as string
  const schema = searchParams.get('schema') || undefined
  const warehouse = searchParams.get('warehouse') || undefined

  const [activeTab, setActiveTab] = useState('overview')

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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Database className="w-8 h-8 text-primary-600" />
          {tableName}
        </h1>
        {schema && (
          <p className="text-gray-600 mt-1">
            Schema: {schema}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
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
