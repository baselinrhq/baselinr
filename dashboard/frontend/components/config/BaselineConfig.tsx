'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Select, SelectOption } from '@/components/ui/Select'

export interface BaselineConfigProps {
  baselines: Record<string, unknown>
  onChange: (baselines: Record<string, unknown>) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const BASELINE_STRATEGIES: SelectOption[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'last_run', label: 'Last Run' },
  { value: 'moving_average', label: 'Moving Average' },
  { value: 'prior_period', label: 'Prior Period' },
  { value: 'stable_window', label: 'Stable Window' },
]

export function BaselineConfig({
  baselines,
  onChange,
  errors,
  isLoading,
}: BaselineConfigProps) {
  const [strategy, setStrategy] = useState<string>(
    (baselines?.strategy as string) || 'last_run'
  )
  const [movingAverage, setMovingAverage] = useState<number>(
    ((baselines?.windows as Record<string, unknown>)?.moving_average as number) || 7
  )
  const [priorPeriod, setPriorPeriod] = useState<number>(
    ((baselines?.windows as Record<string, unknown>)?.prior_period as number) || 7
  )
  const [minRuns, setMinRuns] = useState<number>(
    ((baselines?.windows as Record<string, unknown>)?.min_runs as number) || 3
  )

  useEffect(() => {
    if (baselines) {
      setStrategy((baselines.strategy as string) || 'last_run')
      const windows = (baselines.windows as Record<string, unknown>) || {}
      setMovingAverage((windows.moving_average as number) || 7)
      setPriorPeriod((windows.prior_period as number) || 7)
      setMinRuns((windows.min_runs as number) || 3)
    }
  }, [baselines])

  const handleStrategyChange = (value: string) => {
    setStrategy(value)
    onChange({
      ...baselines,
      strategy: value,
    })
  }

  const handleWindowChange = (key: string, value: number) => {
    const windows = ((baselines?.windows as Record<string, unknown>) || {}) as Record<string, number>
    const newWindows = {
      ...windows,
      [key]: value,
    }
    onChange({
      ...baselines,
      windows: newWindows,
    })
  }

  const getStrategyDescription = (strategyValue: string): string => {
    switch (strategyValue) {
      case 'auto':
        return 'Automatically selects the best baseline based on data stability'
      case 'last_run':
        return 'Uses the previous profiling run as the baseline'
      case 'moving_average':
        return 'Uses the average of the last N runs as the baseline'
      case 'prior_period':
        return 'Uses the same period from the previous cycle (day/week/month)'
      case 'stable_window':
        return 'Uses the most stable window of recent runs'
      default:
        return ''
    }
  }

  return (
    <Card>
      <div className="p-6 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-white mb-1">Baseline Selection</h4>
          <p className="text-xs text-slate-400">
            Configure how the baseline is selected for drift comparison
          </p>
        </div>

        <FormField
          label="Baseline Strategy"
          error={errors?.baselines}
          required
        >
          <Select
            value={strategy}
            onChange={handleStrategyChange}
            options={BASELINE_STRATEGIES}
            disabled={isLoading}
          />
          {strategy && (
            <p className="text-xs text-slate-400 mt-2">{getStrategyDescription(strategy)}</p>
          )}
        </FormField>

        {(strategy === 'moving_average' || strategy === 'auto') && (
          <FormField
            label="Moving Average Window"
            error={errors?.moving_average}
            helperText="Number of runs to include in the moving average"
          >
            <Input
              type="number"
              value={movingAverage}
              onChange={(e) => {
                const value = Number(e.target.value)
                setMovingAverage(value)
                handleWindowChange('moving_average', value)
              }}
              min={1}
              max={30}
              disabled={isLoading}
            />
          </FormField>
        )}

        {(strategy === 'prior_period' || strategy === 'auto') && (
          <FormField
            label="Prior Period (Days)"
            error={errors?.prior_period}
            helperText="Days for prior period comparison (1=day, 7=week, 30=month)"
          >
            <Input
              type="number"
              value={priorPeriod}
              onChange={(e) => {
                const value = Number(e.target.value)
                setPriorPeriod(value)
                handleWindowChange('prior_period', value)
              }}
              min={1}
              max={365}
              disabled={isLoading}
            />
          </FormField>
        )}

        {strategy === 'auto' && (
          <FormField
            label="Minimum Runs Required"
            error={errors?.min_runs}
            helperText="Minimum number of runs required before auto-selection is available"
          >
            <Input
              type="number"
              value={minRuns}
              onChange={(e) => {
                const value = Number(e.target.value)
                setMinRuns(value)
                handleWindowChange('min_runs', value)
              }}
              min={1}
              max={10}
              disabled={isLoading}
            />
          </FormField>
        )}
      </div>
    </Card>
  )
}

