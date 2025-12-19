'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'
import { Checkbox } from '@/components/ui/Checkbox'

export interface StatisticalStrategyConfigProps {
  statistical: Record<string, unknown>
  onChange: (statistical: Record<string, unknown>) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const SENSITIVITY_OPTIONS: SelectOption[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const AVAILABLE_TESTS = [
  { id: 'ks_test', label: 'Kolmogorov-Smirnov Test', description: 'Distribution comparison test' },
  { id: 'psi', label: 'Population Stability Index', description: 'PSI for distribution shifts' },
  { id: 'z_score', label: 'Z-Score Test', description: 'Mean/variance shift detection' },
  { id: 'chi_square', label: 'Chi-Square Test', description: 'Categorical distribution test' },
  { id: 'entropy', label: 'Entropy Change', description: 'Entropy change detection' },
  { id: 'top_k', label: 'Top-K Stability', description: 'Top category stability' },
]

export function StatisticalStrategyConfig({
  statistical,
  onChange,
  errors,
  isLoading,
}: StatisticalStrategyConfigProps) {
  const [tests, setTests] = useState<string[]>(
    (statistical?.tests as string[]) || ['ks_test', 'psi', 'chi_square']
  )
  const [sensitivity, setSensitivity] = useState<string>(
    (statistical?.sensitivity as string) || 'medium'
  )
  const [testParams, setTestParams] = useState<Record<string, Record<string, number>>>(
    (statistical?.test_params as Record<string, Record<string, number>>) || {
      ks_test: { alpha: 0.05 },
      psi: { buckets: 10, threshold: 0.2 },
      z_score: { z_threshold: 2.0 },
      chi_square: { alpha: 0.05 },
      entropy: { entropy_threshold: 0.1 },
      top_k: { k: 10, similarity_threshold: 0.7 },
    }
  )

  useEffect(() => {
    if (statistical) {
      setTests((statistical.tests as string[]) || ['ks_test', 'psi', 'chi_square'])
      setSensitivity((statistical.sensitivity as string) || 'medium')
      setTestParams(
        (statistical.test_params as Record<string, Record<string, number>>) || {
          ks_test: { alpha: 0.05 },
          psi: { buckets: 10, threshold: 0.2 },
          z_score: { z_threshold: 2.0 },
          chi_square: { alpha: 0.05 },
          entropy: { entropy_threshold: 0.1 },
          top_k: { k: 10, similarity_threshold: 0.7 },
        }
      )
    }
  }, [statistical])

  const handleTestToggle = (testId: string, checked: boolean) => {
    const newTests = checked
      ? [...tests, testId]
      : tests.filter((t) => t !== testId)
    setTests(newTests)
    onChange({
      ...statistical,
      tests: newTests,
      sensitivity,
      test_params: testParams,
    })
  }

  const handleSensitivityChange = (value: string) => {
    setSensitivity(value)
    onChange({
      ...statistical,
      tests,
      sensitivity: value,
      test_params: testParams,
    })
  }

  const handleTestParamChange = (testId: string, paramKey: string, value: number) => {
    const newTestParams = {
      ...testParams,
      [testId]: {
        ...(testParams[testId] || {}),
        [paramKey]: value,
      },
    }
    setTestParams(newTestParams)
    onChange({
      ...statistical,
      tests,
      sensitivity,
      test_params: newTestParams,
    })
  }

  return (
    <Card>
      <div className="p-6 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-1">Statistical Test Configuration</h4>
          <p className="text-xs text-gray-600">
            Configure statistical tests for advanced drift detection
          </p>
        </div>

        <FormField
          label="Sensitivity"
          error={errors?.sensitivity}
          helperText="Overall sensitivity level for statistical tests"
        >
          <Select
            value={sensitivity}
            onChange={handleSensitivityChange}
            options={SENSITIVITY_OPTIONS}
            disabled={isLoading}
          />
        </FormField>

        <FormField
          label="Statistical Tests"
          error={errors?.tests}
          helperText="Select which statistical tests to run"
        >
          <div className="space-y-3">
            {AVAILABLE_TESTS.map((test) => (
              <div key={test.id} className="flex items-start gap-3">
                <Checkbox
                  checked={tests.includes(test.id)}
                  onChange={(e) => handleTestToggle(test.id, e.target.checked)}
                  disabled={isLoading}
                />
                <div className="flex-1">
                  <label className="text-sm font-medium text-gray-900 cursor-pointer">
                    {test.label}
                  </label>
                  <p className="text-xs text-gray-600">{test.description}</p>
                </div>
              </div>
            ))}
          </div>
        </FormField>

        {/* Test-specific parameters */}
        {tests.length > 0 && (
          <div className="space-y-4 border-t pt-4">
            <h5 className="text-sm font-medium text-gray-900">Test Parameters</h5>
            {tests.includes('ks_test') && (
              <FormField
                label="KS Test - Alpha (Significance Level)"
                helperText="Significance level for the Kolmogorov-Smirnov test"
              >
                <Input
                  type="number"
                  value={testParams.ks_test?.alpha || 0.05}
                  onChange={(e) => handleTestParamChange('ks_test', 'alpha', Number(e.target.value))}
                  min={0.001}
                  max={0.5}
                  step={0.001}
                  disabled={isLoading}
                />
              </FormField>
            )}

            {tests.includes('psi') && (
              <div className="space-y-3">
                <FormField
                  label="PSI - Buckets"
                  helperText="Number of buckets for distribution comparison"
                >
                  <Input
                    type="number"
                    value={testParams.psi?.buckets || 10}
                    onChange={(e) => handleTestParamChange('psi', 'buckets', Number(e.target.value))}
                    min={5}
                    max={50}
                    disabled={isLoading}
                  />
                </FormField>
                <FormField
                  label="PSI - Threshold"
                  helperText="PSI threshold for drift detection"
                >
                  <Input
                    type="number"
                    value={testParams.psi?.threshold || 0.2}
                    onChange={(e) => handleTestParamChange('psi', 'threshold', Number(e.target.value))}
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    disabled={isLoading}
                  />
                </FormField>
              </div>
            )}

            {tests.includes('z_score') && (
              <FormField
                label="Z-Score - Threshold"
                helperText="Z-score threshold (standard deviations)"
              >
                <Input
                  type="number"
                  value={testParams.z_score?.z_threshold || 2.0}
                  onChange={(e) => handleTestParamChange('z_score', 'z_threshold', Number(e.target.value))}
                  min={1.0}
                  max={5.0}
                  step={0.1}
                  disabled={isLoading}
                />
              </FormField>
            )}

            {tests.includes('chi_square') && (
              <FormField
                label="Chi-Square - Alpha (Significance Level)"
                helperText="Significance level for the chi-square test"
              >
                <Input
                  type="number"
                  value={testParams.chi_square?.alpha || 0.05}
                  onChange={(e) => handleTestParamChange('chi_square', 'alpha', Number(e.target.value))}
                  min={0.001}
                  max={0.5}
                  step={0.001}
                  disabled={isLoading}
                />
              </FormField>
            )}

            {tests.includes('entropy') && (
              <FormField
                label="Entropy - Threshold"
                helperText="Threshold for entropy change detection"
              >
                <Input
                  type="number"
                  value={testParams.entropy?.entropy_threshold || 0.1}
                  onChange={(e) => handleTestParamChange('entropy', 'entropy_threshold', Number(e.target.value))}
                  min={0.01}
                  max={1.0}
                  step={0.01}
                  disabled={isLoading}
                />
              </FormField>
            )}

            {tests.includes('top_k') && (
              <div className="space-y-3">
                <FormField
                  label="Top-K - K (Number of Categories)"
                  helperText="Number of top categories to track"
                >
                  <Input
                    type="number"
                    value={testParams.top_k?.k || 10}
                    onChange={(e) => handleTestParamChange('top_k', 'k', Number(e.target.value))}
                    min={5}
                    max={50}
                    disabled={isLoading}
                  />
                </FormField>
                <FormField
                  label="Top-K - Similarity Threshold"
                  helperText="Similarity threshold for category stability"
                >
                  <Input
                    type="number"
                    value={testParams.top_k?.similarity_threshold || 0.7}
                    onChange={(e) => handleTestParamChange('top_k', 'similarity_threshold', Number(e.target.value))}
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    disabled={isLoading}
                  />
                </FormField>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

