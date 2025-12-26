'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { fetchValidationFailureSamples } from '@/lib/api'
import type { ValidationFailureSamples } from '@/types/validation'

interface FailureSamplesProps {
  resultId: number | null
  isOpen: boolean
  onClose: () => void
}

export default function FailureSamples({ resultId, isOpen, onClose }: FailureSamplesProps) {
  const { data: samples, isLoading } = useQuery<ValidationFailureSamples>({
    queryKey: ['validation-failure-samples', resultId],
    queryFn: () => fetchValidationFailureSamples(resultId!),
    enabled: isOpen && resultId !== null,
  })

  const handleExport = () => {
    if (!samples) return

    const dataStr = JSON.stringify(samples.sample_failures, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `validation-failures-${resultId}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Failure Samples"
      size="xl"
    >
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      ) : !samples ? (
        <div className="text-center py-8 text-slate-400">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
          <p>Failed to load failure samples</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Summary */}
          <Card>
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-400">Total Failures</p>
                  <p className="text-2xl font-bold text-white mt-1">{samples.total_failures?.toLocaleString() || '0'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-400">Sample Size</p>
                  <p className="text-2xl font-bold text-white mt-1">
                    {samples.sample_failures.length} {samples.sample_failures.length < samples.total_failures && `of ${samples.total_failures}`}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExport}
                  icon={<Download className="w-4 h-4" />}
                >
                  Export JSON
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Failure Patterns */}
          {samples.failure_patterns && Object.keys(samples.failure_patterns).length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-white">Failure Patterns</h3>
              </CardHeader>
              <CardBody>
                <div className="space-y-2">
                  {Object.entries(samples.failure_patterns).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between p-2 bg-surface-700/50 rounded">
                      <span className="text-sm font-medium text-slate-300">{key}:</span>
                      <span className="text-sm text-white">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Sample Failures Table */}
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold text-white">Sample Failed Rows</h3>
            </CardHeader>
            <CardBody>
              {samples.sample_failures.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-surface-800/60">
                      <tr>
                        {Object.keys(samples.sample_failures[0]).map((key) => (
                          <th
                            key={key}
                            className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase tracking-wider"
                          >
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-700/50">
                      {samples.sample_failures.map((row, index) => (
                        <tr key={index} className="hover:bg-surface-700/30 transition-colors">
                          {Object.entries(row).map(([key, value]) => (
                            <td key={key} className="px-4 py-2 text-sm text-white">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
                  <p>No sample failures available</p>
                  <p className="text-xs mt-1">
                    Detailed failure samples may not be available for all validation types
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Note about failure reason */}
          {samples.sample_failures.length === 0 && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-400">Limited Sample Data</p>
                  <p className="text-sm text-amber-400/80 mt-1">
                    Detailed failure samples are not available for this validation result. 
                    Check the validation result details for the failure reason.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

