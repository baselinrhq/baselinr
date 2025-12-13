'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { GitBranch, AlertTriangle, Clock } from 'lucide-react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { getEventsTimeline } from '@/lib/api/rca'
import type { EventTimelineItem } from '@/types/rca'
// Helper functions for date formatting
const formatDateTime = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

const subDays = (date: Date, days: number): Date => {
  const result = new Date(date)
  result.setDate(result.getDate() - days)
  return result
}

const formatDate = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface RCATimelineProps {
  assetName?: string
}

const eventTypeIcons = {
  anomaly: AlertTriangle,
  pipeline_run: GitBranch,
  code_deployment: GitBranch,
}

const eventTypeColors = {
  anomaly: 'bg-red-500',
  pipeline_run: 'bg-blue-500',
  code_deployment: 'bg-purple-500',
}

export default function RCATimeline({ assetName }: RCATimelineProps) {
  const [startTime, setStartTime] = useState(formatDateTime(subDays(new Date(), 7)))
  const [endTime, setEndTime] = useState(formatDateTime(new Date()))
  const [filterAsset, setFilterAsset] = useState(assetName || '')

  const { data: timelineItems, isLoading } = useQuery<EventTimelineItem[]>({
    queryKey: ['rca-timeline', startTime, endTime, filterAsset],
    queryFn: () =>
      getEventsTimeline({
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        asset_name: filterAsset || undefined,
      }),
    enabled: !!startTime && !!endTime,
  })

  const handleQuickRange = (days: number) => {
    setEndTime(formatDateTime(new Date()))
    setStartTime(formatDateTime(subDays(new Date(), days)))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  const sortedItems = timelineItems
    ? [...timelineItems].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      )
    : []

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Timeline Filters</h3>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Start Time
              </label>
              <Input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                End Time
              </label>
              <Input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Asset Name
              </label>
              <Input
                type="text"
                value={filterAsset}
                onChange={(e) => setFilterAsset(e.target.value)}
                placeholder="Filter by asset..."
              />
            </div>
            <div className="flex items-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleQuickRange(7)}>
                7d
              </Button>
              <Button variant="secondary" size="sm" onClick={() => handleQuickRange(30)}>
                30d
              </Button>
              <Button variant="secondary" size="sm" onClick={() => handleQuickRange(90)}>
                90d
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Events Timeline</h3>
        </CardHeader>
        <CardBody>
          {sortedItems.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Clock className="w-12 h-12 mx-auto mb-4 text-slate-500" />
              <p>No events found in the selected time range</p>
            </div>
          ) : (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-surface-700" />

              {/* Timeline items */}
              <div className="space-y-6">
                {sortedItems.map((item, index) => {
                  const EventIcon = eventTypeIcons[item.event_type as keyof typeof eventTypeIcons] || AlertTriangle
                  const eventColor =
                    eventTypeColors[item.event_type as keyof typeof eventTypeColors] || 'bg-slate-500'

                  return (
                    <div key={index} className="relative flex items-start gap-4">
                      {/* Timeline marker */}
                      <div className="relative z-10 flex-shrink-0">
                        <div
                          className={`w-4 h-4 rounded-full ${eventColor} border-2 border-surface-800 shadow-sm`}
                        />
                      </div>

                      {/* Event content */}
                      <div className="flex-1 bg-surface-800/50 border border-surface-700/50 rounded-lg p-4 hover:border-surface-600 transition-colors">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <EventIcon className="w-4 h-4 text-slate-400" />
                            <Badge
                              variant={
                                item.event_type === 'anomaly'
                                  ? 'error'
                                  : item.event_type === 'pipeline_run'
                                  ? 'info'
                                  : 'default'
                              }
                              size="sm"
                            >
                              {item.event_type.replace('_', ' ')}
                            </Badge>
                            <span className="text-xs text-slate-400">
                              {formatDate(item.timestamp)}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-400">Relevance:</span>
                            <Badge variant="default" size="sm">
                              {(item.relevance_score * 100).toFixed(0)}%
                            </Badge>
                          </div>
                        </div>

                        {/* Event data preview */}
                        <div className="mt-2">
                          <pre className="text-xs bg-surface-900/50 text-slate-300 p-2 rounded overflow-x-auto max-h-32 overflow-y-auto">
                            {JSON.stringify(item.event_data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

