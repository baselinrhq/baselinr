'use client'

import { useState } from 'react'
import { StorageConfig } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Toggle } from '@/components/ui/Toggle'
import { Slider } from '@/components/ui/Slider'
import { Checkbox } from '@/components/ui/Checkbox'
import { Card } from '@/components/ui/Card'
import { Info } from 'lucide-react'
import { Tooltip } from '@/components/ui/Tooltip'

export interface AnomalyConfigProps {
  storage: StorageConfig
  onChange: (storage: StorageConfig) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const ANOMALY_METHODS = [
  { value: 'control_limits', label: 'Control Limits', description: 'Shewhart control charts using mean and standard deviation' },
  { value: 'iqr', label: 'IQR (Interquartile Range)', description: 'Detects outliers using quartile boundaries' },
  { value: 'mad', label: 'MAD (Median Absolute Deviation)', description: 'Modified z-score using median-based statistics' },
  { value: 'ewma', label: 'EWMA (Exponentially Weighted Moving Average)', description: 'Time-weighted moving average for trend detection' },
  { value: 'seasonality', label: 'Seasonality Detection', description: 'Detects seasonal patterns and trends' },
  { value: 'regime_shift', label: 'Regime Shift Detection', description: 'Statistical tests for distribution changes' },
] as const

export function AnomalyConfig({
  storage,
  onChange,
  errors = {},
  isLoading = false,
}: AnomalyConfigProps) {
  const [expandedMethods, setExpandedMethods] = useState<Set<string>>(new Set(['control_limits', 'iqr']))

  const handleChange = (field: keyof StorageConfig, value: unknown) => {
    onChange({ ...storage, [field]: value })
  }

  const enableAnomalyDetection = storage.enable_anomaly_detection ?? false
  const enabledMethods = storage.anomaly_enabled_methods ?? [
    'control_limits',
    'iqr',
    'mad',
    'ewma',
    'seasonality',
    'regime_shift',
  ]
  const iqrThreshold = storage.anomaly_iqr_threshold ?? 1.5
  const madThreshold = storage.anomaly_mad_threshold ?? 3.0
  const ewmaDeviationThreshold = storage.anomaly_ewma_deviation_threshold ?? 2.0
  const seasonalityEnabled = storage.anomaly_seasonality_enabled ?? true
  const regimeShiftEnabled = storage.anomaly_regime_shift_enabled ?? true
  const regimeShiftWindow = storage.anomaly_regime_shift_window ?? 3
  const regimeShiftSensitivity = storage.anomaly_regime_shift_sensitivity ?? 0.05

  const handleMethodToggle = (method: string, checked: boolean) => {
    const currentMethods = enabledMethods || []
    if (checked) {
      if (!currentMethods.includes(method)) {
        handleChange('anomaly_enabled_methods', [...currentMethods, method])
      }
    } else {
      handleChange('anomaly_enabled_methods', currentMethods.filter((m) => m !== method))
    }
  }

  const toggleMethodExpansion = (method: string) => {
    const newExpanded = new Set(expandedMethods)
    if (newExpanded.has(method)) {
      newExpanded.delete(method)
    } else {
      newExpanded.add(method)
    }
    setExpandedMethods(newExpanded)
  }

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-white">Anomaly Detection</h3>
            <Tooltip content="Anomaly detection automatically identifies unusual patterns in your profiling metrics using learned expectations. Multiple detection methods can be enabled simultaneously.">
              <span>
                <Info className="w-4 h-4 text-slate-400 cursor-help" />
              </span>
            </Tooltip>
          </div>
          <p className="text-sm text-slate-400">
            Configure automatic anomaly detection using learned expectations from historical data.
          </p>
        </div>

        {/* Enable Toggle */}
        <FormField
          label="Enable Anomaly Detection"
          helperText="Automatically detect anomalies using learned expectations"
        >
          <Toggle
            checked={enableAnomalyDetection}
            onChange={(checked) => handleChange('enable_anomaly_detection', checked)}
            disabled={isLoading}
            label="Enable anomaly detection"
          />
        </FormField>

        {enableAnomalyDetection && (
          <div className="space-y-6 pl-4 border-l-2 border-surface-700/50">
            {/* Detection Methods */}
            <FormField
              label="Detection Methods"
              helperText="Select one or more methods to use for anomaly detection"
              error={errors.anomaly_enabled_methods}
            >
              <div className="space-y-3">
                {ANOMALY_METHODS.map((method) => {
                  const isEnabled = enabledMethods.includes(method.value)
                  const isExpanded = expandedMethods.has(method.value)
                  
                  return (
                    <div key={method.value} className="border border-surface-700/50 rounded-lg p-3">
                      <div className="flex items-start gap-3">
                        <Checkbox
                          checked={isEnabled}
                          onChange={(e) => handleMethodToggle(method.value, e.target.checked)}
                          disabled={isLoading}
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <div>
                              <label className="text-sm font-medium text-white">
                                {method.label}
                              </label>
                              <p className="text-xs text-slate-400 mt-0.5">{method.description}</p>
                            </div>
                            {isEnabled && (
                              <button
                                type="button"
                                onClick={() => toggleMethodExpansion(method.value)}
                                className="text-xs text-cyan-400 hover:text-cyan-300"
                              >
                                {isExpanded ? 'Hide settings' : 'Show settings'}
                              </button>
                            )}
                          </div>

                          {/* Method-specific settings */}
                          {isEnabled && isExpanded && (
                            <div className="mt-3 pt-3 border-t border-surface-700/50 space-y-4">
                              {/* IQR Threshold */}
                              {method.value === 'iqr' && (
                                <FormField
                                  label="IQR Threshold"
                                  helperText="IQR multiplier for outlier detection (default: 1.5)"
                                  error={errors.anomaly_iqr_threshold}
                                >
                                  <div className="space-y-2">
                                    <Slider
                                      value={iqrThreshold}
                                      onChange={(value) => handleChange('anomaly_iqr_threshold', value as number)}
                                      min={0.1}
                                      max={5.0}
                                      step={0.1}
                                      showValue
                                      disabled={isLoading}
                                    />
                                    <div className="flex items-center gap-2">
                                      <Input
                                        type="number"
                                        value={iqrThreshold.toFixed(1)}
                                        onChange={(e) => {
                                          const val = parseFloat(e.target.value)
                                          if (!isNaN(val) && val >= 0.1 && val <= 5.0) {
                                            handleChange('anomaly_iqr_threshold', val)
                                          }
                                        }}
                                        min={0.1}
                                        max={5.0}
                                        step={0.1}
                                        disabled={isLoading}
                                        className="w-24"
                                      />
                                      <span className="text-sm text-slate-400">
                                        (Standard: 1.5, Lower = more sensitive)
                                      </span>
                                    </div>
                                  </div>
                                </FormField>
                              )}

                              {/* MAD Threshold */}
                              {method.value === 'mad' && (
                                <FormField
                                  label="MAD Threshold"
                                  helperText="Modified z-score threshold for MAD detection (default: 3.0)"
                                  error={errors.anomaly_mad_threshold}
                                >
                                  <div className="space-y-2">
                                    <Slider
                                      value={madThreshold}
                                      onChange={(value) => handleChange('anomaly_mad_threshold', value as number)}
                                      min={1.0}
                                      max={10.0}
                                      step={0.1}
                                      showValue
                                      disabled={isLoading}
                                    />
                                    <div className="flex items-center gap-2">
                                      <Input
                                        type="number"
                                        value={madThreshold.toFixed(1)}
                                        onChange={(e) => {
                                          const val = parseFloat(e.target.value)
                                          if (!isNaN(val) && val >= 1.0 && val <= 10.0) {
                                            handleChange('anomaly_mad_threshold', val)
                                          }
                                        }}
                                        min={1.0}
                                        max={10.0}
                                        step={0.1}
                                        disabled={isLoading}
                                        className="w-24"
                                      />
                                      <span className="text-sm text-slate-400">
                                        (Lower = more sensitive)
                                      </span>
                                    </div>
                                  </div>
                                </FormField>
                              )}

                              {/* EWMA Deviation Threshold */}
                              {method.value === 'ewma' && (
                                <FormField
                                  label="EWMA Deviation Threshold"
                                  helperText="Number of standard deviations for EWMA-based detection (default: 2.0)"
                                  error={errors.anomaly_ewma_deviation_threshold}
                                >
                                  <div className="space-y-2">
                                    <Slider
                                      value={ewmaDeviationThreshold}
                                      onChange={(value) => handleChange('anomaly_ewma_deviation_threshold', value as number)}
                                      min={0.5}
                                      max={5.0}
                                      step={0.1}
                                      showValue
                                      disabled={isLoading}
                                    />
                                    <div className="flex items-center gap-2">
                                      <Input
                                        type="number"
                                        value={ewmaDeviationThreshold.toFixed(1)}
                                        onChange={(e) => {
                                          const val = parseFloat(e.target.value)
                                          if (!isNaN(val) && val >= 0.5 && val <= 5.0) {
                                            handleChange('anomaly_ewma_deviation_threshold', val)
                                          }
                                        }}
                                        min={0.5}
                                        max={5.0}
                                        step={0.1}
                                        disabled={isLoading}
                                        className="w-24"
                                      />
                                      <span className="text-sm text-slate-400">
                                        (Lower = more sensitive)
                                      </span>
                                    </div>
                                  </div>
                                </FormField>
                              )}

                              {/* Seasonality Toggle */}
                              {method.value === 'seasonality' && (
                                <FormField
                                  label="Enable Seasonality Detection"
                                  helperText="Detect trends and seasonal patterns in time-series data"
                                >
                                  <Toggle
                                    checked={seasonalityEnabled}
                                    onChange={(checked) => handleChange('anomaly_seasonality_enabled', checked)}
                                    disabled={isLoading}
                                    label="Enable seasonality and trend detection"
                                  />
                                </FormField>
                              )}

                              {/* Regime Shift Settings */}
                              {method.value === 'regime_shift' && (
                                <>
                                  <FormField
                                    label="Enable Regime Shift Detection"
                                    helperText="Detect statistical changes in data distribution"
                                  >
                                    <Toggle
                                      checked={regimeShiftEnabled}
                                      onChange={(checked) => handleChange('anomaly_regime_shift_enabled', checked)}
                                      disabled={isLoading}
                                      label="Enable regime shift detection"
                                    />
                                  </FormField>

                                  {regimeShiftEnabled && (
                                    <div className="space-y-4">
                                      <FormField
                                        label="Window Size"
                                        helperText="Number of recent runs for regime shift comparison (default: 3)"
                                        error={errors.anomaly_regime_shift_window}
                                      >
                                        <Input
                                          type="number"
                                          value={regimeShiftWindow}
                                          onChange={(e) => {
                                            const val = parseInt(e.target.value, 10)
                                            if (!isNaN(val) && val >= 2) {
                                              handleChange('anomaly_regime_shift_window', val)
                                            }
                                          }}
                                          min={2}
                                          disabled={isLoading}
                                          className="w-32"
                                        />
                                      </FormField>

                                      <FormField
                                        label="Sensitivity (P-value)"
                                        helperText="P-value threshold for regime shift detection (default: 0.05)"
                                        error={errors.anomaly_regime_shift_sensitivity}
                                      >
                                        <div className="space-y-2">
                                          <Slider
                                            value={regimeShiftSensitivity}
                                            onChange={(value) => handleChange('anomaly_regime_shift_sensitivity', value as number)}
                                            min={0.01}
                                            max={0.2}
                                            step={0.01}
                                            showValue
                                            disabled={isLoading}
                                          />
                                          <div className="flex items-center gap-2">
                                            <Input
                                              type="number"
                                              value={regimeShiftSensitivity.toFixed(2)}
                                              onChange={(e) => {
                                                const val = parseFloat(e.target.value)
                                                if (!isNaN(val) && val > 0 && val <= 1) {
                                                  handleChange('anomaly_regime_shift_sensitivity', val)
                                                }
                                              }}
                                              min={0.01}
                                              max={1.0}
                                              step={0.01}
                                              disabled={isLoading}
                                              className="w-24"
                                            />
                                            <span className="text-sm text-slate-400">
                                              (Lower = more sensitive)
                                            </span>
                                          </div>
                                        </div>
                                      </FormField>
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </FormField>

            {enabledMethods.length === 0 && (
              <div className="p-4 glass-card border-amber-500/30 bg-amber-500/10 rounded-lg">
                <p className="text-sm text-amber-300">
                  <strong>Warning:</strong> At least one detection method must be enabled for anomaly detection to work.
                </p>
              </div>
            )}
          </div>
        )}

        {!enableAnomalyDetection && (
          <div className="p-4 glass-card border-cyan-500/30 bg-cyan-500/10 rounded-lg">
            <p className="text-sm text-cyan-300">
              <strong>Info:</strong> Enable anomaly detection to automatically identify unusual patterns in your profiling metrics.
              Make sure expectation learning is also enabled for best results.
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}

export default AnomalyConfig

