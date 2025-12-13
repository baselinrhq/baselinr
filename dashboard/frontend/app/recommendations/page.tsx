'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { fetchRecommendations, refreshRecommendations } from '@/lib/api/recommendations'
import { listConnections } from '@/lib/api/connections'
import RecommendationList from '@/components/recommendations/RecommendationList'
import ApplyRecommendations from '@/components/recommendations/ApplyRecommendations'
import type { RecommendationOptions } from '@/lib/api/recommendations'

export default function RecommendationsPage() {
  const [connectionId, setConnectionId] = useState<string>('')
  const [schema, setSchema] = useState<string>('')
  const [includeColumns, setIncludeColumns] = useState(false)
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [selectedTables, setSelectedTables] = useState<Array<{ schema: string; table: string; database?: string }>>([])

  // Fetch connections
  const { data: connectionsData } = useQuery({
    queryKey: ['connections'],
    queryFn: () => listConnections(),
  })

  // Fetch recommendations
  const recommendationOptions: RecommendationOptions = {
    connection_id: connectionId,
    schema: schema || undefined,
    include_columns: includeColumns,
  }

  const { data: recommendations, isLoading, refetch } = useQuery({
    queryKey: ['recommendations', recommendationOptions],
    queryFn: () => fetchRecommendations(recommendationOptions),
    enabled: !!connectionId,
  })

  const handleRefresh = async () => {
    if (!connectionId) return
    await refreshRecommendations(recommendationOptions)
    refetch()
  }

  const handleApplyClick = (tables: Array<{ schema: string; table: string; database?: string }>) => {
    setSelectedTables(tables)
    setShowApplyModal(true)
  }

  const handleApplySuccess = () => {
    setShowApplyModal(false)
    setSelectedTables([])
    refetch()
  }

  const connections = connectionsData?.connections || []

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Sparkles className="w-7 h-7 text-amber-400" />
            </div>
            Recommendations
            <span className="px-2 py-0.5 text-xs font-medium bg-purple-500/20 text-purple-300 rounded-full">
              AI
            </span>
          </h1>
          <p className="text-slate-400 mt-2">AI-powered table and column selection recommendations</p>
        </div>
        {connectionId && (
          <Button onClick={handleRefresh} variant="primary" disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
      </div>

      {/* Connection Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Connection Settings</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select
              label="Connection"
              value={connectionId}
              onChange={(value) => setConnectionId(value)}
              placeholder="Select a connection"
              options={[
                { value: '', label: 'Select a connection' },
                ...connections.map((conn) => ({
                  value: conn.id,
                  label: conn.name,
                })),
              ]}
            />
            <Input
              label="Schema (optional)"
              type="text"
              value={schema}
              onChange={(e) => setSchema(e.target.value)}
              placeholder="Leave empty for all schemas"
            />
            <div className="flex items-end pb-1">
              <label className="flex items-center space-x-3 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={includeColumns}
                    onChange={(e) => setIncludeColumns(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-5 h-5 border-2 border-surface-600 rounded bg-surface-800 peer-checked:bg-cyan-500 peer-checked:border-cyan-500 peer-focus:ring-2 peer-focus:ring-cyan-500/50 transition-colors">
                    {includeColumns && (
                      <svg className="w-full h-full text-white p-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
                <span className="text-sm font-medium text-slate-300">Include column recommendations</span>
              </label>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Recommendations */}
      {!connectionId && (
        <Card>
          <CardBody>
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-surface-800 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-slate-600" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Select a Connection</h3>
              <p className="text-slate-400">Choose a connection to generate recommendations</p>
            </div>
          </CardBody>
        </Card>
      )}

      {connectionId && isLoading && (
        <Card>
          <CardBody>
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          </CardBody>
        </Card>
      )}

      {connectionId && !isLoading && recommendations && (
        <>
          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Recommendation Summary</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-surface-800/50">
                  <div className="text-sm text-slate-400">Total Analyzed</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {recommendations.total_tables_analyzed}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-success-500/10">
                  <div className="text-sm text-slate-400">Recommended</div>
                  <div className="text-2xl font-bold text-success-400 mt-1">
                    {recommendations.total_recommended}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-surface-800/50">
                  <div className="text-sm text-slate-400">Excluded</div>
                  <div className="text-2xl font-bold text-slate-400 mt-1">
                    {recommendations.total_excluded}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-surface-800/50">
                  <div className="text-sm text-slate-400">Database Type</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {recommendations.database_type}
                  </div>
                </div>
              </div>
              {recommendations.total_columns_analyzed > 0 && (
                <div className="mt-4 pt-4 border-t border-surface-700/50">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-surface-800/50">
                      <div className="text-sm text-slate-400">Columns Analyzed</div>
                      <div className="text-xl font-bold text-white mt-1">
                        {recommendations.total_columns_analyzed}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-success-500/10">
                      <div className="text-sm text-slate-400">Checks Recommended</div>
                      <div className="text-xl font-bold text-success-400 mt-1">
                        {recommendations.total_column_checks_recommended}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Recommendations List */}
          <RecommendationList
            recommendations={recommendations.recommended_tables}
            onApply={handleApplyClick}
          />
        </>
      )}

      {/* Apply Modal */}
      {showApplyModal && (
        <ApplyRecommendations
          connectionId={connectionId}
          selectedTables={selectedTables}
          onClose={() => setShowApplyModal(false)}
          onSuccess={handleApplySuccess}
        />
      )}
    </div>
  )
}
