'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { fetchDriftDetails, fetchDriftImpact } from '@/lib/api'
import type { DriftDetails as DriftDetailsType, DriftImpact } from '@/types/drift'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import Link from 'next/link'

interface DriftDetailsProps {
  eventId: string
  isOpen: boolean
  onClose: () => void
}

export default function DriftDetails({ eventId, isOpen, onClose }: DriftDetailsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'comparison' | 'statistics' | 'impact'>('overview')

  const { data: details, isLoading: detailsLoading } = useQuery<DriftDetailsType>({
    queryKey: ['drift-details', eventId],
    queryFn: () => fetchDriftDetails(eventId),
    enabled: isOpen && !!eventId,
  })

  const { data: impact, isLoading: impactLoading } = useQuery<DriftImpact>({
    queryKey: ['drift-impact', eventId],
    queryFn: () => fetchDriftImpact(eventId),
    enabled: isOpen && !!eventId,
  })

  if (!isOpen) return null

  const event = details?.event

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Drift Event Details"
      size="xl"
    >
      {detailsLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      ) : !details || !event ? (
        <div className="text-center py-8 text-gray-500">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p>Failed to load drift details</p>
        </div>
      ) : (
        <div className="space-y-4">
          <Tabs
            tabs={[
              { id: 'overview', label: 'Overview' },
              { id: 'comparison', label: 'Before/After' },
              { id: 'statistics', label: 'Statistical Tests' },
              { id: 'impact', label: 'Impact Analysis' },
            ]}
            activeTab={activeTab}
            onChange={(tabId) => setActiveTab(tabId as typeof activeTab)}
          />
          
          <div className="space-y-4">
            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <h3 className="text-lg font-semibold text-gray-900">Event Information</h3>
                    </CardHeader>
                    <CardBody>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-gray-500">Table</p>
                          <p className="font-medium text-gray-900">{event.table_name}</p>
                        </div>
                        {event.column_name && (
                          <div>
                            <p className="text-sm text-gray-500">Column</p>
                            <p className="font-medium text-gray-900">{event.column_name}</p>
                          </div>
                        )}
                        <div>
                          <p className="text-sm text-gray-500">Metric</p>
                          <p className="font-medium text-gray-900">{event.metric_name}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500">Severity</p>
                          <Badge
                            variant={
                              event.severity === 'high'
                                ? 'error'
                                : event.severity === 'medium'
                                ? 'warning'
                                : 'success'
                            }
                          >
                            {event.severity}
                          </Badge>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500">Detected At</p>
                          <p className="font-medium text-gray-900">
                            {new Date(event.timestamp || event.detected_at || '').toLocaleString()}
                          </p>
                        </div>
                        {event.change_percent !== undefined && event.change_percent !== null && (
                          <div>
                            <p className="text-sm text-gray-500">Change</p>
                            <p
                              className={`font-medium ${
                                event.change_percent > 0 ? 'text-red-600' : 'text-green-600'
                              }`}
                            >
                              {event.change_percent > 0 ? '+' : ''}
                              {event.change_percent.toFixed(1)}%
                            </p>
                          </div>
                        )}
                      </div>
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <Link
                          href={`/tables/${encodeURIComponent(event.table_name)}`}
                          className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-800"
                        >
                          View table details
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </div>
                    </CardBody>
                  </Card>

                  {/* Values Comparison */}
                  <Card>
                    <CardHeader>
                      <h3 className="text-lg font-semibold text-gray-900">Value Comparison</h3>
                    </CardHeader>
                    <CardBody>
                      <div className="grid grid-cols-2 gap-6">
                        <div>
                          <p className="text-sm font-medium text-gray-500 mb-2">Baseline Value</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {event.baseline_value !== undefined && event.baseline_value !== null
                              ? typeof event.baseline_value === 'number'
                                ? event.baseline_value.toFixed(2)
                                : String(event.baseline_value)
                              : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-500 mb-2">Current Value</p>
                          <p className="text-2xl font-bold text-gray-900">
                            {event.current_value !== undefined && event.current_value !== null
                              ? typeof event.current_value === 'number'
                                ? event.current_value.toFixed(2)
                                : String(event.current_value)
                              : 'N/A'}
                          </p>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
              </div>
            )}

            {/* Before/After Comparison Tab */}
            {activeTab === 'comparison' && (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <h3 className="text-lg font-semibold text-gray-900">Baseline vs Current Metrics</h3>
                    </CardHeader>
                    <CardBody>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-medium text-gray-900 mb-3">Baseline</h4>
                          <div className="space-y-2">
                            {Object.keys(details.baseline_metrics).length > 0 ? (
                              Object.entries(details.baseline_metrics).map(([key, value]) => (
                                <div key={key} className="flex justify-between py-2 border-b border-gray-100">
                                  <span className="text-sm text-gray-600">{key}</span>
                                  <span className="text-sm font-medium text-gray-900">
                                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                                  </span>
                                </div>
                              ))
                            ) : (
                              <p className="text-sm text-gray-500">No baseline metrics available</p>
                            )}
                          </div>
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-3">Current</h4>
                          <div className="space-y-2">
                            {Object.keys(details.current_metrics).length > 0 ? (
                              Object.entries(details.current_metrics).map(([key, value]) => {
                                const baselineValue = details.baseline_metrics[key]
                                const hasChange =
                                  baselineValue !== undefined &&
                                  value !== undefined &&
                                  baselineValue !== value
                                return (
                                  <div
                                    key={key}
                                    className={`flex justify-between py-2 border-b border-gray-100 ${
                                      hasChange ? 'bg-yellow-50' : ''
                                    }`}
                                  >
                                    <span className="text-sm text-gray-600">{key}</span>
                                    <span className="text-sm font-medium text-gray-900">
                                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                                    </span>
                                  </div>
                                )
                              })
                            ) : (
                              <p className="text-sm text-gray-500">No current metrics available</p>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardBody>
                  </Card>

                  {/* Historical Values Chart */}
                  {details.historical_values.length > 0 && (
                    <Card>
                      <CardHeader>
                        <h3 className="text-lg font-semibold text-gray-900">Historical Trend</h3>
                      </CardHeader>
                      <CardBody>
                        <ResponsiveContainer width="100%" height={300}>
                          <LineChart
                            data={[
                              ...details.historical_values.map((h) => ({
                                date: new Date(h.timestamp).toLocaleDateString(),
                                value: h.value,
                              })),
                              {
                                date: 'Current',
                                value:
                                  event.current_value !== undefined && event.current_value !== null
                                    ? Number(event.current_value)
                                    : null,
                              },
                            ]}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line
                              type="monotone"
                              dataKey="value"
                              stroke="#3b82f6"
                              strokeWidth={2}
                              name="Metric Value"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </CardBody>
                    </Card>
                  )}
                </div>
            )}

            {/* Statistical Tests Tab */}
            {activeTab === 'statistics' && (
              <div className="space-y-4">
                  {details.statistical_tests && details.statistical_tests.length > 0 ? (
                    <Card>
                      <CardHeader>
                        <h3 className="text-lg font-semibold text-gray-900">Statistical Test Results</h3>
                      </CardHeader>
                      <CardBody>
                        <div className="space-y-4">
                          {details.statistical_tests.map((test, index) => (
                            <div
                              key={index}
                              className="p-4 border border-gray-200 rounded-lg"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900">{test.test_name}</h4>
                                <Badge
                                  variant={test.significant ? 'error' : 'success'}
                                >
                                  {test.result}
                                </Badge>
                              </div>
                              {test.p_value !== undefined && (
                                <p className="text-sm text-gray-600">p-value: {test.p_value.toFixed(4)}</p>
                              )}
                              {test.statistic !== undefined && (
                                <p className="text-sm text-gray-600">Statistic: {test.statistic.toFixed(4)}</p>
                              )}
                              {test.interpretation && (
                                <p className="text-sm text-gray-500 mt-2">{test.interpretation}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </CardBody>
                    </Card>
                  ) : (
                    <Card>
                      <CardBody>
                        <p className="text-center text-gray-500 py-8">
                          No statistical test results available for this event
                        </p>
                      </CardBody>
                    </Card>
                  )}
              </div>
            )}

            {/* Impact Analysis Tab */}
            {activeTab === 'impact' && (
              <div className="space-y-4">
                  {impactLoading ? (
                    <div className="flex items-center justify-center h-64">
                      <LoadingSpinner />
                    </div>
                  ) : impact ? (
                    <>
                      <Card>
                        <CardHeader>
                          <h3 className="text-lg font-semibold text-gray-900">Impact Assessment</h3>
                        </CardHeader>
                        <CardBody>
                          <div className="space-y-4">
                            <div>
                              <p className="text-sm text-gray-500 mb-1">Impact Score</p>
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full ${
                                      impact.impact_score >= 0.7
                                        ? 'bg-red-500'
                                        : impact.impact_score >= 0.4
                                        ? 'bg-yellow-500'
                                        : 'bg-green-500'
                                    }`}
                                    style={{ width: `${impact.impact_score * 100}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium text-gray-900">
                                  {(impact.impact_score * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500 mb-1">Affected Metrics</p>
                              <p className="text-lg font-medium text-gray-900">{impact.affected_metrics}</p>
                            </div>
                            {impact.affected_tables.length > 0 && (
                              <div>
                                <p className="text-sm text-gray-500 mb-2">Downstream Tables</p>
                                <div className="space-y-2">
                                  {impact.affected_tables.map((table) => (
                                    <Link
                                      key={table}
                                      href={`/tables/${encodeURIComponent(table)}`}
                                      className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-800"
                                    >
                                      {table}
                                      <ExternalLink className="w-3 h-3" />
                                    </Link>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </CardBody>
                      </Card>

                      {impact.recommendations.length > 0 && (
                        <Card>
                          <CardHeader>
                            <h3 className="text-lg font-semibold text-gray-900">Recommendations</h3>
                          </CardHeader>
                          <CardBody>
                            <ul className="space-y-2">
                              {impact.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-start gap-2">
                                  <span className="text-primary-600 mt-1">•</span>
                                  <span className="text-sm text-gray-700">{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </CardBody>
                        </Card>
                      )}
                    </>
                  ) : (
                    <Card>
                      <CardBody>
                        <p className="text-center text-gray-500 py-8">
                          Failed to load impact analysis
                        </p>
                      </CardBody>
                    </Card>
                  )}

                  {/* Related Events */}
                  {details.related_events.length > 0 && (
                    <Card>
                      <CardHeader>
                        <h3 className="text-lg font-semibold text-gray-900">Related Events</h3>
                      </CardHeader>
                      <CardBody>
                        <div className="space-y-2">
                          {details.related_events.map((relatedEvent) => (
                            <div
                              key={relatedEvent.event_id}
                              className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-medium text-gray-900">
                                    {relatedEvent.metric_name}
                                  </p>
                                  <p className="text-sm text-gray-500">
                                    {new Date(relatedEvent.timestamp || relatedEvent.detected_at || '').toLocaleString()}
                                  </p>
                                </div>
                                <Badge
                                  variant={
                                    relatedEvent.severity === 'high'
                                      ? 'error'
                                      : relatedEvent.severity === 'medium'
                                      ? 'warning'
                                      : 'success'
                                  }
                                >
                                  {relatedEvent.severity}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardBody>
                    </Card>
                  )}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}

