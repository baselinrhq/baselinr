'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-yellow-500" />
            Smart Recommendations
          </h1>
          <p className="text-gray-600 mt-1">AI-powered table and column selection recommendations</p>
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Connection
              </label>
              <select
                value={connectionId}
                onChange={(e) => setConnectionId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select a connection</option>
                {connections.map((conn) => (
                  <option key={conn.id} value={conn.id}>
                    {conn.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Schema (optional)
              </label>
              <input
                type="text"
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                placeholder="Leave empty for all schemas"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeColumns}
                  onChange={(e) => setIncludeColumns(e.target.checked)}
                  className="w-4 h-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="text-sm font-medium text-gray-700">Include column recommendations</span>
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
              <Sparkles className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Connection</h3>
              <p className="text-gray-600">Choose a connection to generate recommendations</p>
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
                <div>
                  <div className="text-sm text-gray-600">Total Analyzed</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {recommendations.total_tables_analyzed}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Recommended</div>
                  <div className="text-2xl font-bold text-green-600">
                    {recommendations.total_recommended}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Excluded</div>
                  <div className="text-2xl font-bold text-gray-600">
                    {recommendations.total_excluded}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Database Type</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {recommendations.database_type}
                  </div>
                </div>
              </div>
              {recommendations.total_columns_analyzed > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Columns Analyzed</div>
                      <div className="text-xl font-bold text-gray-900">
                        {recommendations.total_columns_analyzed}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Checks Recommended</div>
                      <div className="text-xl font-bold text-green-600">
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


