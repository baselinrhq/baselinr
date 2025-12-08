'use client'

import { useState } from 'react'
import { Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select, SelectOption } from '@/components/ui/Select'
import { ValidationRuleConfig } from '@/types/config'
import { testRule, RuleTestResult } from '@/lib/api/validation'

export interface RuleTestPreviewProps {
  rule: ValidationRuleConfig
  connectionId?: string
}

const SAMPLE_SIZE_OPTIONS: SelectOption[] = [
  { value: '10', label: '10 rows' },
  { value: '50', label: '50 rows' },
  { value: '100', label: '100 rows' },
]

export function RuleTestPreview({ rule, connectionId }: RuleTestPreviewProps) {
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<RuleTestResult | null>(null)
  const [testError, setTestError] = useState<string | null>(null)
  const [sampleSize, setSampleSize] = useState<number>(10)

  const handleTest = async () => {
    if (!rule.table || !rule.column) {
      setTestError('Table and column are required for testing')
      return
    }

    setIsTesting(true)
    setTestError(null)
    setTestResult(null)

    try {
      const result = await testRule(rule, connectionId, sampleSize)
      setTestResult(result)
    } catch (error) {
      setTestError(error instanceof Error ? error.message : 'Failed to test rule')
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-gray-900">Test Rule</h4>
          <p className="text-xs text-gray-600 mt-1">
            Test this rule on sample data from the table
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={String(sampleSize)}
            onChange={(value) => setSampleSize(Number(value))}
            options={SAMPLE_SIZE_OPTIONS}
            className="w-32"
          />
          <Button
            onClick={handleTest}
            disabled={isTesting || !rule.table || !rule.column}
            icon={isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : undefined}
          >
            {isTesting ? 'Testing...' : 'Test Rule'}
          </Button>
        </div>
      </div>

      {testError && (
        <Card className="bg-red-50 border-red-200">
          <div className="flex items-start gap-2 p-4">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-900">Test Failed</p>
              <p className="text-sm text-red-700 mt-1">{testError}</p>
            </div>
          </div>
        </Card>
      )}

      {testResult && (
        <Card>
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {testResult.passed ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-medium text-green-900">All tests passed</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-red-600" />
                    <span className="text-sm font-medium text-red-900">
                      {testResult.failed_count} of {testResult.sample_size} tests failed
                    </span>
                  </>
                )}
              </div>
              <div className="text-sm text-gray-600">
                {testResult.passed_count} passed, {testResult.failed_count} failed
              </div>
            </div>

            {testResult.failures.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-900">Failures:</p>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {testResult.failures.map((failure, index) => (
                    <div
                      key={index}
                      className="bg-red-50 border border-red-200 rounded p-3 text-sm"
                    >
                      <p className="font-medium text-red-900 mb-1">
                        Row {index + 1}
                      </p>
                      <p className="text-red-700 mb-2">{failure.reason}</p>
                      <details className="text-xs">
                        <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                          View row data
                        </summary>
                        <pre className="mt-2 p-2 bg-white rounded border text-xs overflow-x-auto">
                          {JSON.stringify(failure.row, null, 2)}
                        </pre>
                      </details>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {!testResult && !testError && (
        <Card className="bg-gray-50">
          <div className="p-4 text-center text-sm text-gray-600">
            Click &quot;Test Rule&quot; to validate this rule against sample data from the table
          </div>
        </Card>
      )}
    </div>
  )
}

