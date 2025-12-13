'use client'

import { StorageConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Toggle } from '@/components/ui/Toggle'
import { Slider } from '@/components/ui/Slider'
import { Card } from '@/components/ui/Card'
import { Info } from 'lucide-react'
import { Tooltip } from '@/components/ui/Tooltip'

export interface ExpectationLearningProps {
  storage: StorageConfig
  onChange: (storage: StorageConfig) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

export function ExpectationLearning({
  storage,
  onChange,
  errors = {},
  isLoading = false,
}: ExpectationLearningProps) {
  const handleChange = (field: keyof StorageConfig, value: unknown) => {
    onChange({ ...storage, [field]: value })
  }

  const enableExpectationLearning = storage.enable_expectation_learning ?? false
  const learningWindowDays = storage.learning_window_days ?? 30
  const minSamples = storage.min_samples ?? 5
  const ewmaLambda = storage.ewma_lambda ?? 0.2

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-white">Expectation Learning</h3>
            <Tooltip content="Expectation learning automatically builds statistical models of your data over time. These learned expectations are used by anomaly detection to identify unusual patterns.">
              <span>
                <Info className="w-4 h-4 text-slate-400 cursor-help" />
              </span>
            </Tooltip>
          </div>
          <p className="text-sm text-slate-400">
            Configure how Baselinr learns expected metric ranges from historical profiling data.
            These expectations enable automatic anomaly detection.
          </p>
        </div>

        {/* Enable Toggle */}
        <FormField
          label="Enable Expectation Learning"
          helperText="Automatically learn expected metric ranges from historical profiling runs"
        >
          <Toggle
            checked={enableExpectationLearning}
            onChange={(checked) => handleChange('enable_expectation_learning', checked)}
            disabled={isLoading}
            label="Enable expectation learning"
          />
        </FormField>

        {enableExpectationLearning && (
          <div className="space-y-6 pl-4 border-l-2 border-surface-700/50">
            {/* Learning Window */}
            <FormField
              label="Learning Window (Days)"
              helperText="Number of days of historical data to use for learning expectations"
              error={errors.learning_window_days}
            >
              <div className="space-y-2">
                <Slider
                  value={learningWindowDays}
                  onChange={(value) => handleChange('learning_window_days', value as number)}
                  min={7}
                  max={365}
                  step={1}
                  showValue
                  disabled={isLoading}
                />
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={learningWindowDays}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10)
                      if (!isNaN(val) && val >= 7 && val <= 365) {
                        handleChange('learning_window_days', val)
                      }
                    }}
                    min={7}
                    max={365}
                    disabled={isLoading}
                    className="w-24"
                  />
                  <span className="text-sm text-slate-400">days</span>
                </div>
                <p className="text-xs text-slate-400">
                  Longer windows provide more stable expectations but may include outdated patterns.
                  Shorter windows adapt faster but may be less reliable.
                </p>
              </div>
            </FormField>

            {/* Min Samples */}
            <FormField
              label="Minimum Samples"
              helperText="Minimum number of historical runs required before learning expectations"
              error={errors.min_samples}
            >
              <div className="space-y-2">
                <Input
                  type="number"
                  value={minSamples}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10)
                    if (!isNaN(val) && val >= 1) {
                      handleChange('min_samples', val)
                    }
                  }}
                  min={1}
                  disabled={isLoading}
                  className="w-32"
                />
                <p className="text-xs text-slate-400">
                  If fewer runs are available, expectations will not be learned for that metric.
                  Recommended: 5-10 for stable expectations.
                </p>
              </div>
            </FormField>

            {/* EWMA Lambda */}
            <FormField
              label="EWMA Smoothing Parameter (Lambda)"
              helperText="Exponentially Weighted Moving Average smoothing parameter for trend detection"
              error={errors.ewma_lambda}
            >
              <div className="space-y-2">
                <Slider
                  value={ewmaLambda}
                  onChange={(value) => handleChange('ewma_lambda', value as number)}
                  min={0.01}
                  max={1.0}
                  step={0.01}
                  showValue
                  disabled={isLoading}
                />
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={ewmaLambda.toFixed(2)}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value)
                      if (!isNaN(val) && val > 0 && val <= 1) {
                        handleChange('ewma_lambda', val)
                      }
                    }}
                    min={0.01}
                    max={1.0}
                    step={0.01}
                    disabled={isLoading}
                    className="w-24"
                  />
                  <span className="text-sm text-slate-400">(0.01 - 1.0)</span>
                </div>
                <p className="text-xs text-slate-400">
                  Lower values (e.g., 0.1) give more weight to older data (smoother).
                  Higher values (e.g., 0.3) give more weight to recent data (more reactive).
                </p>
              </div>
            </FormField>
          </div>
        )}

        {!enableExpectationLearning && (
          <div className="p-4 glass-card border-amber-500/30 bg-amber-500/10 rounded-lg">
            <p className="text-sm text-amber-300">
              <strong>Note:</strong> Expectation learning must be enabled for anomaly detection to work effectively.
              Anomaly detection uses learned expectations to identify unusual patterns in your data.
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}

export default ExpectationLearning

