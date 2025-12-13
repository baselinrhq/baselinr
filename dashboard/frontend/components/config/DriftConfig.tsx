'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Select, SelectOption } from '@/components/ui/Select'
import { DriftDetectionConfig } from '@/types/config'
import { ThresholdConfig } from './ThresholdConfig'
import { StatisticalStrategyConfig } from './StatisticalStrategyConfig'

export interface DriftConfigProps {
  driftDetection: DriftDetectionConfig
  onChange: (driftDetection: DriftDetectionConfig) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const STRATEGY_OPTIONS: SelectOption[] = [
  { value: 'absolute_threshold', label: 'Absolute Threshold' },
  { value: 'standard_deviation', label: 'Standard Deviation' },
  { value: 'statistical', label: 'Statistical Tests' },
  { value: 'ml_based', label: 'ML-Based (Coming Soon)' },
]

export function DriftConfig({
  driftDetection,
  onChange,
  errors,
  isLoading,
}: DriftConfigProps) {
  const [strategy, setStrategy] = useState<string>(
    driftDetection?.strategy || 'absolute_threshold'
  )

  useEffect(() => {
    if (driftDetection) {
      setStrategy(driftDetection.strategy || 'absolute_threshold')
    }
  }, [driftDetection])

  const handleStrategyChange = (value: string) => {
    setStrategy(value)
    onChange({
      ...driftDetection,
      strategy: value,
    })
  }

  const handleAbsoluteThresholdChange = (thresholds: Record<string, number>) => {
    onChange({
      ...driftDetection,
      absolute_threshold: thresholds,
    })
  }

  const handleStandardDeviationChange = (thresholds: Record<string, number>) => {
    onChange({
      ...driftDetection,
      standard_deviation: thresholds,
    })
  }

  const handleStatisticalChange = (statistical: Record<string, unknown>) => {
    onChange({
      ...driftDetection,
      statistical,
    })
  }

  const getStrategyDescription = (strategyValue: string): string => {
    switch (strategyValue) {
      case 'absolute_threshold':
        return 'Classifies drift based on absolute percentage change from baseline. Simple and intuitive.'
      case 'standard_deviation':
        return 'Classifies drift based on standard deviations from the mean. Good for normally distributed data.'
      case 'statistical':
        return 'Uses statistical tests (KS, PSI, Chi-square, etc.) for advanced drift detection. More accurate but computationally intensive.'
      case 'ml_based':
        return 'Machine learning based drift detection (coming soon).'
      default:
        return ''
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Drift Detection Strategy
            </h3>
            <p className="text-sm text-slate-400">
              Select the strategy for detecting data drift in your tables
            </p>
          </div>

          <FormField
            label="Detection Strategy"
            error={errors?.strategy}
            required
          >
            <Select
              value={strategy}
              onChange={handleStrategyChange}
              options={STRATEGY_OPTIONS}
              disabled={isLoading || strategy === 'ml_based'}
            />
            {strategy && (
              <p className="text-xs text-slate-400 mt-2">{getStrategyDescription(strategy)}</p>
            )}
          </FormField>

          {/* Strategy-specific configuration */}
          {strategy === 'absolute_threshold' && (
            <ThresholdConfig
              thresholds={driftDetection?.absolute_threshold || {
                low_threshold: 5.0,
                medium_threshold: 15.0,
                high_threshold: 30.0,
              }}
              onChange={handleAbsoluteThresholdChange}
              unit="%"
              min={0}
              max={100}
              step={0.1}
              errors={errors}
            />
          )}

          {strategy === 'standard_deviation' && (
            <ThresholdConfig
              thresholds={driftDetection?.standard_deviation || {
                low_threshold: 1.0,
                medium_threshold: 2.0,
                high_threshold: 3.0,
              }}
              onChange={handleStandardDeviationChange}
              unit="σ"
              min={0}
              max={5}
              step={0.1}
              errors={errors}
            />
          )}

          {strategy === 'statistical' && (
            <StatisticalStrategyConfig
              statistical={driftDetection?.statistical || {}}
              onChange={handleStatisticalChange}
              errors={errors}
              isLoading={isLoading}
            />
          )}

          {strategy === 'ml_based' && (
            <div className="glass-card border-amber-500/30 bg-amber-500/10 rounded-lg p-4">
              <p className="text-sm text-amber-300">
                ML-based drift detection is coming soon. This strategy is not yet available.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

