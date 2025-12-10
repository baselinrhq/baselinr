'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Shield } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Tabs } from '@/components/ui/Tabs'
import { fetchValidationResults } from '@/lib/api'
import ValidationFilters from '@/components/validation/ValidationFilters'
import ValidationOverview from '@/components/validation/ValidationOverview'
import ValidationResults from '@/components/validation/ValidationResults'
import FailureSamples from '@/components/validation/FailureSamples'
import type { ValidationFilters as ValidationFiltersType } from '@/types/validation'

export default function ValidationPage() {
  const [filters, setFilters] = useState<ValidationFiltersType>({
    days: 30,
  })
  const [activeTab, setActiveTab] = useState('overview')
  const [page, setPage] = useState(1)
  const [selectedResultId, setSelectedResultId] = useState<number | null>(null)
  const [showFailureModal, setShowFailureModal] = useState(false)

  // Convert filters to API format
  const apiFilters = {
    table: filters.table,
    schema: filters.schema,
    rule_type: filters.rule_type,
    severity: filters.severity,
    passed: filters.passed,
    days: filters.days || 30,
    page,
    page_size: 50,
  }

  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['validation-results', apiFilters],
    queryFn: () => fetchValidationResults(apiFilters),
  })

  const handleExport = async () => {
    try {
      // Export functionality - can be enhanced later
      const data = resultsData?.results || []
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `baselinr-validation-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const handleRowClick = (resultId: number) => {
    setSelectedResultId(resultId)
    setShowFailureModal(true)
  }

  // Extract unique warehouses and tables for filter suggestions
  const warehouses: string[] = [] // Can be populated from summary if needed
  const tables = Array.from(new Set(resultsData?.results.map((r) => r.table_name).filter(Boolean) || []))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-8 h-8 text-blue-500" />
            Validation Dashboard
          </h1>
          <p className="text-gray-600 mt-1">View validation results and execution history</p>
        </div>
        <Button onClick={handleExport} variant="primary">
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Filters */}
      <ValidationFilters
        filters={filters}
        onChange={setFilters}
        warehouses={warehouses}
        tables={tables}
      />

      {/* Main Content with Tabs */}
      <div className="space-y-4">
        <Tabs
          tabs={[
            { id: 'overview', label: 'Overview' },
            { id: 'results', label: 'Results' },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />

        <div className="space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <ValidationOverview
              warehouse={filters.warehouse}
              days={filters.days || 30}
            />
          )}

          {/* Results Tab */}
          {activeTab === 'results' && (
            <ValidationResults
              results={resultsData?.results || []}
              onRowClick={handleRowClick}
              page={page}
              pageSize={50}
              total={resultsData?.total || 0}
              onPageChange={setPage}
              isLoading={isLoading}
            />
          )}
        </div>
      </div>

      {/* Failure Samples Modal */}
      {selectedResultId !== null && (
        <FailureSamples
          resultId={selectedResultId}
          isOpen={showFailureModal}
          onClose={() => {
            setShowFailureModal(false)
            setSelectedResultId(null)
          }}
        />
      )}
    </div>
  )
}

