'use client'

import { useState, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, List, Grid, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui'
import { SearchInput } from '@/components/ui'
import { LoadingSpinner } from '@/components/ui'
import { Badge } from '@/components/ui'
import { fetchQualityScores } from '@/lib/api'
import ScoreBadge from '@/components/quality/ScoreBadge'
import { formatDate } from '@/lib/utils'
import { debounce } from '@/lib/utils'

type ViewMode = 'list' | 'grid'
type SortField = 'table_name' | 'overall_score' | 'status' | 'calculated_at'
type SortOrder = 'asc' | 'desc'

export default function QualityScoresPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [filters, setFilters] = useState<{ schema?: string; status?: string }>({})
  const [sortField, setSortField] = useState<SortField>('overall_score')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [searchQuery, setSearchQuery] = useState('')

  // Debounced search - use ref to maintain stable debounced function
  const debouncedSetSearchRef = useRef(
    debounce((value: string) => {
      setSearchQuery(value)
    }, 300)
  )

  const handleSearchChange = useCallback((value: string) => {
    // Update immediately for UI responsiveness
    setSearchQuery(value)
    // Also trigger debounced update
    debouncedSetSearchRef.current(value)
  }, [])

  // Fetch quality scores
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['quality-scores', filters],
    queryFn: () => fetchQualityScores(filters),
    staleTime: 30000,
  })

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-4 h-4 text-slate-500" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-4 h-4 text-cyan-400" />
    ) : (
      <ArrowDown className="w-4 h-4 text-cyan-400" />
    )
  }

  // Sort and filter scores
  const processedScores = data?.scores
    ? [...data.scores]
        .filter((score) => {
          if (searchQuery) {
            const query = searchQuery.toLowerCase()
            const tableName = score.table_name.toLowerCase()
            const schemaName = (score.schema_name || '').toLowerCase()
            return tableName.includes(query) || schemaName.includes(query)
          }
          return true
        })
        .sort((a, b) => {
          let aValue: string | number
          let bValue: string | number

          switch (sortField) {
            case 'table_name':
              aValue = `${a.schema_name || ''}.${a.table_name}`.toLowerCase()
              bValue = `${b.schema_name || ''}.${b.table_name}`.toLowerCase()
              break
            case 'overall_score':
              aValue = a.overall_score
              bValue = b.overall_score
              break
            case 'status':
              aValue = a.status
              bValue = b.status
              break
            case 'calculated_at':
              aValue = new Date(a.calculated_at).getTime()
              bValue = new Date(b.calculated_at).getTime()
              break
            default:
              return 0
          }

          if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
          if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
          return 0
        })
    : []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-lg font-medium text-slate-400">Error loading quality scores</div>
          <p className="text-sm text-slate-500 mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button onClick={() => refetch()} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <TrendingUp className="w-6 h-6 text-emerald-400" />
            </div>
            Quality Scores
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Monitor data quality across all tables
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'list' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="w-4 h-4 mr-2" />
            List
          </Button>
          <Button
            variant={viewMode === 'grid' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="w-4 h-4 mr-2" />
            Grid
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <SearchInput
            placeholder="Search by table name or schema..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </div>
        <div className="flex gap-2">
          <select
            value={filters.schema || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                schema: e.target.value || undefined,
              }))
            }
            className="px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          >
            <option value="">All Schemas</option>
            {/* TODO: Fetch available schemas */}
          </select>
          <select
            value={filters.status || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                status: e.target.value || undefined,
              }))
            }
            className="px-3 py-2 bg-surface-800/50 border border-surface-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          >
            <option value="">All Statuses</option>
            <option value="healthy">Healthy</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      {/* Results */}
      {!data || processedScores.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-slate-400">No quality scores found</p>
        </div>
      ) : (
        <>
          <div className="text-sm text-slate-400">
            Showing {processedScores.length} of {data.total} scores
          </div>

          {viewMode === 'list' ? (
            <div className="glass-card rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-surface-800/60">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        <button
                          onClick={() => handleSort('table_name')}
                          className="flex items-center gap-2 hover:text-slate-300"
                        >
                          Table Name
                          {getSortIcon('table_name')}
                        </button>
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        <button
                          onClick={() => handleSort('overall_score')}
                          className="flex items-center gap-2 hover:text-slate-300"
                        >
                          Score
                          {getSortIcon('overall_score')}
                        </button>
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        <button
                          onClick={() => handleSort('status')}
                          className="flex items-center gap-2 hover:text-slate-300"
                        >
                          Status
                          {getSortIcon('status')}
                        </button>
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Trend
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        <button
                          onClick={() => handleSort('calculated_at')}
                          className="flex items-center gap-2 hover:text-slate-300"
                        >
                          Calculated
                          {getSortIcon('calculated_at')}
                        </button>
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Issues
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-700/50">
                    {processedScores.map((score) => (
                      <tr
                        key={`${score.schema_name || ''}.${score.table_name}`}
                        className="hover:bg-surface-800/30 transition-colors"
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Link
                            href={`/quality/${encodeURIComponent(score.table_name)}${
                              score.schema_name
                                ? `?schema=${encodeURIComponent(score.schema_name)}`
                                : ''
                            }`}
                            className="text-sm font-medium text-white hover:text-cyan-400 transition-colors"
                          >
                            {score.schema_name
                              ? `${score.schema_name}.${score.table_name}`
                              : score.table_name}
                          </Link>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <ScoreBadge score={score.overall_score} status={score.status} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Badge
                            variant={
                              score.status === 'healthy'
                                ? 'success'
                                : score.status === 'warning'
                                ? 'warning'
                                : 'error'
                            }
                            size="sm"
                          >
                            {score.status}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {score.trend && score.trend_percentage !== null ? (
                            <div className="flex items-center gap-1 text-sm">
                              {score.trend === 'improving' && (
                                <span className="text-emerald-400">
                                  ↑ +{score.trend_percentage.toFixed(1)}%
                                </span>
                              )}
                              {score.trend === 'degrading' && (
                                <span className="text-rose-400">
                                  ↓ {score.trend_percentage.toFixed(1)}%
                                </span>
                              )}
                              {score.trend === 'stable' && (
                                <span className="text-slate-500">→ Stable</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 text-sm">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                          {formatDate(score.calculated_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2 text-sm">
                            {score.issues.critical > 0 && (
                              <span className="text-rose-400 font-medium">
                                {score.issues.critical} critical
                              </span>
                            )}
                            {score.issues.warnings > 0 && (
                              <span className="text-amber-400">
                                {score.issues.warnings} warnings
                              </span>
                            )}
                            {score.issues.total === 0 && (
                              <span className="text-slate-500">No issues</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {processedScores.map((score) => (
                <Link
                  key={`${score.schema_name || ''}.${score.table_name}`}
                  href={`/quality/${encodeURIComponent(score.table_name)}${
                    score.schema_name
                      ? `?schema=${encodeURIComponent(score.schema_name)}`
                      : ''
                  }`}
                >
                  <div className="glass-card hover:border-surface-600 transition-all p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white">
                          {score.schema_name
                            ? `${score.schema_name}.${score.table_name}`
                            : score.table_name}
                        </h3>
                      </div>
                      <ScoreBadge score={score.overall_score} status={score.status} />
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">Status</span>
                        <Badge
                          variant={
                            score.status === 'healthy'
                              ? 'success'
                              : score.status === 'warning'
                              ? 'warning'
                              : 'error'
                          }
                          size="sm"
                        >
                          {score.status}
                        </Badge>
                      </div>
                      {score.trend && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-400">Trend</span>
                          <span className="text-sm">
                            {score.trend === 'improving' && (
                              <span className="text-emerald-400">
                                ↑ +{score.trend_percentage?.toFixed(1) || '0.0'}%
                              </span>
                            )}
                            {score.trend === 'degrading' && (
                              <span className="text-rose-400">
                                ↓ {score.trend_percentage?.toFixed(1) || '0.0'}%
                              </span>
                            )}
                            {score.trend === 'stable' && (
                              <span className="text-slate-500">→ Stable</span>
                            )}
                          </span>
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">Issues</span>
                        <span className="text-sm text-slate-300">
                          {score.issues.total} total
                        </span>
                      </div>
                      <div className="pt-2 border-t border-surface-700/50">
                        <p className="text-xs text-slate-500">
                          {formatDate(score.calculated_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

