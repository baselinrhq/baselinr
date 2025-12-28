'use client'

import { useState, useEffect } from 'react'
import { QualityScoringConfig as QualityScoringConfigType, QualityScoringWeights, QualityScoringThresholds, QualityScoringFreshness } from '@/types/config'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Toggle } from '@/components/ui/Toggle'
import { AlertCircle } from 'lucide-react'

export interface QualityScoringConfigProps {
  config: QualityScoringConfigType
  onChange: (config: QualityScoringConfigType) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

/**
 * Validate that weights sum to 100
 */
function validateWeights(weights: QualityScoringWeights): string | undefined {
  const total = (weights.completeness || 0) +
    (weights.validity || 0) +
    (weights.consistency || 0) +
    (weights.freshness || 0) +
    (weights.uniqueness || 0) +
    (weights.accuracy || 0)
  
  if (Math.abs(total - 100) > 0.01) {
    return `Weights must sum to 100 (currently ${total.toFixed(1)})`
  }
  
  return undefined
}

/**
 * Validate thresholds are in descending order
 */
function validateThresholds(thresholds: QualityScoringThresholds): string | undefined {
  const healthy = thresholds.healthy || 80
  const warning = thresholds.warning || 60
  const critical = thresholds.critical || 0
  
  if (!(critical <= warning && warning <= healthy)) {
    return 'Thresholds must be in order: critical <= warning <= healthy'
  }
  
  return undefined
}

/**
 * Validate freshness thresholds are in ascending order
 */
function validateFreshness(freshness: QualityScoringFreshness): string | undefined {
  const excellent = freshness.excellent || 24
  const good = freshness.good || 48
  const acceptable = freshness.acceptable || 168
  
  if (!(excellent <= good && good <= acceptable)) {
    return 'Freshness thresholds must be in order: excellent <= good <= acceptable'
  }
  
  return undefined
}

export function QualityScoringConfig({
  config,
  onChange,
  errors = {},
  isLoading = false,
}: QualityScoringConfigProps) {
  const [weights, setWeights] = useState<QualityScoringWeights>(config.weights || {
    completeness: 25,
    validity: 25,
    consistency: 20,
    freshness: 15,
    uniqueness: 10,
    accuracy: 5,
  })
  
  const [thresholds, setThresholds] = useState<QualityScoringThresholds>(config.thresholds || {
    healthy: 80,
    warning: 60,
    critical: 0,
  })
  
  const [freshness, setFreshness] = useState<QualityScoringFreshness>(config.freshness || {
    excellent: 24,
    good: 48,
    acceptable: 168,
  })
  
  const [weightsError, setWeightsError] = useState<string | undefined>()
  const [thresholdsError, setThresholdsError] = useState<string | undefined>()
  const [freshnessError, setFreshnessError] = useState<string | undefined>()

  // Update local state when config changes
  useEffect(() => {
    if (config.weights) setWeights(config.weights)
    if (config.thresholds) setThresholds(config.thresholds)
    if (config.freshness) setFreshness(config.freshness)
  }, [config])

  // Validate and notify parent of changes
  useEffect(() => {
    const weightsErr = validateWeights(weights)
    const thresholdsErr = validateThresholds(thresholds)
    const freshnessErr = validateFreshness(freshness)
    
    setWeightsError(weightsErr)
    setThresholdsError(thresholdsErr)
    setFreshnessError(freshnessErr)
    
    if (!weightsErr && !thresholdsErr && !freshnessErr) {
      onChange({
        ...config,
        weights,
        thresholds,
        freshness,
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weights, thresholds, freshness])

  const updateWeight = (key: keyof QualityScoringWeights, value: number) => {
    setWeights(prev => ({
      ...prev,
      [key]: Math.max(0, Math.min(100, value)),
    }))
  }

  const updateThreshold = (key: keyof QualityScoringThresholds, value: number) => {
    setThresholds(prev => ({
      ...prev,
      [key]: Math.max(0, Math.min(100, value)),
    }))
  }

  const updateFreshness = (key: keyof QualityScoringFreshness, value: number) => {
    setFreshness(prev => ({
      ...prev,
      [key]: Math.max(1, value),
    }))
  }

  const totalWeights = (weights.completeness || 0) +
    (weights.validity || 0) +
    (weights.consistency || 0) +
    (weights.freshness || 0) +
    (weights.uniqueness || 0) +
    (weights.accuracy || 0)

  return (
    <div className="space-y-6">
      {/* Enable/Disable Toggle */}
      <FormField label="Enable Quality Scoring" required={false}>
        <Toggle
          checked={config.enabled ?? true}
          onChange={(checked) => onChange({ ...config, enabled: checked })}
          label="Enable quality scoring"
        />
      </FormField>

      {/* Component Weights */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <FormField label="Component Weights" required>
            <span className="text-xs text-slate-400">Must sum to 100%</span>
          </FormField>
          <div className={`text-sm font-medium ${Math.abs(totalWeights - 100) < 0.01 ? 'text-emerald-400' : 'text-rose-400'}`}>
            Total: {totalWeights.toFixed(1)}%
          </div>
        </div>
        {weightsError && (
          <div className="mb-3 flex items-center gap-2 text-sm text-rose-400">
            <AlertCircle className="w-4 h-4" />
            <span>{weightsError}</span>
          </div>
        )}
        <div className="space-y-3">
          <FormField label="Completeness" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.completeness || 0}
              onChange={(e) => updateWeight('completeness', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
              error={errors.weights}
            />
          </FormField>
          <FormField label="Validity" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.validity || 0}
              onChange={(e) => updateWeight('validity', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Consistency" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.consistency || 0}
              onChange={(e) => updateWeight('consistency', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Freshness" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.freshness || 0}
              onChange={(e) => updateWeight('freshness', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Uniqueness" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.uniqueness || 0}
              onChange={(e) => updateWeight('uniqueness', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Accuracy" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weights.accuracy || 0}
              onChange={(e) => updateWeight('accuracy', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
        </div>
      </div>

      {/* Score Thresholds */}
      <div>
        <FormField label="Score Thresholds" required>
          <span className="text-xs text-slate-400">Must be: critical ≤ warning ≤ healthy</span>
        </FormField>
        {thresholdsError && (
          <div className="mb-3 flex items-center gap-2 text-sm text-rose-400">
            <AlertCircle className="w-4 h-4" />
            <span>{thresholdsError}</span>
          </div>
        )}
        <div className="space-y-3">
          <FormField label="Healthy (≥)" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={thresholds.healthy || 80}
              onChange={(e) => updateThreshold('healthy', parseFloat(e.target.value) || 80)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Warning (≥)" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={thresholds.warning || 60}
              onChange={(e) => updateThreshold('warning', parseFloat(e.target.value) || 60)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Critical (<)" required={false}>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={thresholds.critical || 0}
              onChange={(e) => updateThreshold('critical', parseFloat(e.target.value) || 0)}
              disabled={isLoading}
            />
          </FormField>
        </div>
      </div>

      {/* Freshness Thresholds */}
      <div>
        <FormField label="Freshness Thresholds (hours)" required>
          <span className="text-xs text-slate-400">Must be: excellent ≤ good ≤ acceptable</span>
        </FormField>
        {freshnessError && (
          <div className="mb-3 flex items-center gap-2 text-sm text-rose-400">
            <AlertCircle className="w-4 h-4" />
            <span>{freshnessError}</span>
          </div>
        )}
        <div className="space-y-3">
          <FormField label="Excellent (≤ hours)" required={false}>
            <Input
              type="number"
              min="1"
              step="1"
              value={freshness.excellent || 24}
              onChange={(e) => updateFreshness('excellent', parseInt(e.target.value) || 24)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Good (≤ hours)" required={false}>
            <Input
              type="number"
              min="1"
              step="1"
              value={freshness.good || 48}
              onChange={(e) => updateFreshness('good', parseInt(e.target.value) || 48)}
              disabled={isLoading}
            />
          </FormField>
          <FormField label="Acceptable (≤ hours)" required={false}>
            <Input
              type="number"
              min="1"
              step="1"
              value={freshness.acceptable || 168}
              onChange={(e) => updateFreshness('acceptable', parseInt(e.target.value) || 168)}
              disabled={isLoading}
            />
          </FormField>
        </div>
      </div>

      {/* History Settings */}
      <div>
        <FormField label="History Settings" required={false}>
          <Toggle
            checked={config.store_history ?? true}
            onChange={(checked) => onChange({ ...config, store_history: checked })}
            label="Store score history"
          />
        </FormField>
        {config.store_history && (
          <FormField label="History Retention (days)" required={false}>
            <Input
              type="number"
              min="1"
              step="1"
              value={config.history_retention_days || 90}
              onChange={(e) => onChange({ ...config, history_retention_days: parseInt(e.target.value) || 90 })}
              disabled={isLoading}
            />
          </FormField>
        )}
      </div>
    </div>
  )
}









