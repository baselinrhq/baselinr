'use client'

import { useState, useEffect } from 'react'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Slider } from '@/components/ui/Slider'
import { Card } from '@/components/ui/Card'

export interface ThresholdConfigProps {
  thresholds: Record<string, number>
  onChange: (thresholds: Record<string, number>) => void
  unit?: string
  min?: number
  max?: number
  step?: number
  errors?: Record<string, string>
}

const DEFAULT_THRESHOLDS = {
  low_threshold: 5.0,
  medium_threshold: 15.0,
  high_threshold: 30.0,
}

export function ThresholdConfig({
  thresholds,
  onChange,
  unit = '%',
  min = 0,
  max = 100,
  step = 0.1,
  errors,
}: ThresholdConfigProps) {
  const [lowThreshold, setLowThreshold] = useState<number>(
    thresholds?.low_threshold ?? DEFAULT_THRESHOLDS.low_threshold
  )
  const [mediumThreshold, setMediumThreshold] = useState<number>(
    thresholds?.medium_threshold ?? DEFAULT_THRESHOLDS.medium_threshold
  )
  const [highThreshold, setHighThreshold] = useState<number>(
    thresholds?.high_threshold ?? DEFAULT_THRESHOLDS.high_threshold
  )

  useEffect(() => {
    if (thresholds) {
      setLowThreshold(thresholds.low_threshold ?? DEFAULT_THRESHOLDS.low_threshold)
      setMediumThreshold(thresholds.medium_threshold ?? DEFAULT_THRESHOLDS.medium_threshold)
      setHighThreshold(thresholds.high_threshold ?? DEFAULT_THRESHOLDS.high_threshold)
    }
  }, [thresholds])

  const handleLowChange = (value: number) => {
    const newValue = Math.max(min, Math.min(value, mediumThreshold - step))
    setLowThreshold(newValue)
    onChange({
      ...thresholds,
      low_threshold: newValue,
    })
  }

  const handleMediumChange = (value: number) => {
    const newValue = Math.max(lowThreshold + step, Math.min(value, highThreshold - step))
    setMediumThreshold(newValue)
    onChange({
      ...thresholds,
      medium_threshold: newValue,
    })
  }

  const handleHighChange = (value: number) => {
    const newValue = Math.max(mediumThreshold + step, Math.min(value, max))
    setHighThreshold(newValue)
    onChange({
      ...thresholds,
      high_threshold: newValue,
    })
  }

  const hasError = lowThreshold >= mediumThreshold || mediumThreshold >= highThreshold

  return (
    <Card>
      <div className="p-6 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-1">Threshold Configuration</h4>
          <p className="text-xs text-gray-600">
            Set the thresholds for low, medium, and high severity drift detection
          </p>
        </div>

        {hasError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">
              Thresholds must be in ascending order: Low &lt; Medium &lt; High
            </p>
          </div>
        )}

        <div className="space-y-4">
          <FormField
            label={`Low Severity Threshold (${unit})`}
            error={errors?.low_threshold}
            helperText="Triggers low severity alerts"
          >
            <div className="space-y-2">
              <Slider
                value={lowThreshold}
                onChange={handleLowChange}
                min={min}
                max={Math.min(mediumThreshold - step, max)}
                step={step}
              />
              <Input
                type="number"
                value={lowThreshold}
                onChange={(e) => handleLowChange(Number(e.target.value))}
                min={min}
                max={mediumThreshold - step}
                step={step}
                className="w-32"
              />
            </div>
          </FormField>

          <FormField
            label={`Medium Severity Threshold (${unit})`}
            error={errors?.medium_threshold}
            helperText="Triggers medium severity alerts"
          >
            <div className="space-y-2">
              <Slider
                value={mediumThreshold}
                onChange={handleMediumChange}
                min={lowThreshold + step}
                max={Math.min(highThreshold - step, max)}
                step={step}
              />
              <Input
                type="number"
                value={mediumThreshold}
                onChange={(e) => handleMediumChange(Number(e.target.value))}
                min={lowThreshold + step}
                max={highThreshold - step}
                step={step}
                className="w-32"
              />
            </div>
          </FormField>

          <FormField
            label={`High Severity Threshold (${unit})`}
            error={errors?.high_threshold}
            helperText="Triggers high severity alerts"
          >
            <div className="space-y-2">
              <Slider
                value={highThreshold}
                onChange={handleHighChange}
                min={mediumThreshold + step}
                max={max}
                step={step}
              />
              <Input
                type="number"
                value={highThreshold}
                onChange={(e) => handleHighChange(Number(e.target.value))}
                min={mediumThreshold + step}
                max={max}
                step={step}
                className="w-32"
              />
            </div>
          </FormField>
        </div>
      </div>
    </Card>
  )
}

