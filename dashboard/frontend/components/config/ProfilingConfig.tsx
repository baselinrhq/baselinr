'use client'

import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/Input'
import { Toggle } from '@/components/ui/Toggle'
import { Checkbox } from '@/components/ui/Checkbox'
import { Slider } from '@/components/ui/Slider'
import { Button } from '@/components/ui/Button'
import { ProfilingConfig as ProfilingConfigType } from '@/types/config'

export interface ProfilingConfigProps {
  profiling: ProfilingConfigType
  onChange: (profiling: ProfilingConfigType) => void
  errors?: Record<string, string>
  isLoading?: boolean
}

const ALL_METRICS = [
  'count',
  'null_count',
  'null_ratio',
  'distinct_count',
  'unique_ratio',
  'approx_distinct_count',
  'min',
  'max',
  'mean',
  'stddev',
  'histogram',
  'data_type_inferred',
] as const

const DEFAULT_METRICS = [...ALL_METRICS]

export function ProfilingConfig({
  profiling,
  onChange,
  errors = {},
  isLoading = false,
}: ProfilingConfigProps) {
  const metrics = profiling.metrics || DEFAULT_METRICS
  const allMetricsSelected = metrics.length === ALL_METRICS.length

  const handleChange = (field: keyof ProfilingConfigType, value: unknown) => {
    onChange({ ...profiling, [field]: value })
  }

  const handleMetricToggle = (metric: string, checked: boolean) => {
    const currentMetrics = metrics || []
    if (checked) {
      if (!currentMetrics.includes(metric)) {
        handleChange('metrics', [...currentMetrics, metric])
      }
    } else {
      handleChange('metrics', currentMetrics.filter((m) => m !== metric))
    }
  }

  const handleSelectAllMetrics = () => {
    handleChange('metrics', [...ALL_METRICS])
  }

  const handleDeselectAllMetrics = () => {
    handleChange('metrics', [])
  }

  return (
    <Card>
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Global Profiling Settings
          </h3>
          <p className="text-sm text-slate-400 mb-6">
            Configure default profiling behavior for all tables. These settings can be overridden at the table or column level.
          </p>
        </div>

        {/* Metrics Selection */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-slate-300">Metrics to Compute</h4>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSelectAllMetrics}
                disabled={isLoading || allMetricsSelected}
              >
                Select All
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDeselectAllMetrics}
                disabled={isLoading || metrics.length === 0}
              >
                Deselect All
              </Button>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {ALL_METRICS.map((metric) => (
              <Checkbox
                key={metric}
                label={metric.replace(/_/g, ' ')}
                checked={metrics.includes(metric)}
                onChange={(e) => handleMetricToggle(metric, e.target.checked)}
                disabled={isLoading}
              />
            ))}
          </div>
          
          {errors.metrics && (
            <p className="text-sm text-rose-400">{errors.metrics}</p>
          )}
        </div>

        {/* Histogram Configuration */}
        <div className="space-y-4 border-t border-surface-700/50 pt-4">
          <h4 className="text-sm font-medium text-slate-300">Histogram Configuration</h4>
          
          <FormField
            label="Compute Histograms"
            helperText="Enable histogram computation for numeric columns"
          >
            <Toggle
              checked={profiling.compute_histograms ?? true}
              onChange={(checked) => handleChange('compute_histograms', checked)}
              disabled={isLoading}
            />
          </FormField>

          {profiling.compute_histograms !== false && (
            <FormField
              label="Histogram Bins"
              helperText="Number of bins for histograms (1-100)"
              error={errors.histogram_bins}
            >
              <Input
                type="number"
                value={profiling.histogram_bins ?? 10}
                onChange={(e) =>
                  handleChange(
                    'histogram_bins',
                    e.target.value ? parseInt(e.target.value, 10) : null
                  )
                }
                min={1}
                max={100}
                disabled={isLoading}
              />
            </FormField>
          )}
        </div>

        {/* Max Distinct Values */}
        <div className="space-y-4 border-t border-surface-700/50 pt-4">
          <h4 className="text-sm font-medium text-slate-300">Distinct Values</h4>
          
          <FormField
            label="Max Distinct Values"
            helperText="Maximum number of distinct values to compute (default: 1000)"
            error={errors.max_distinct_values}
          >
            <Input
              type="number"
              value={profiling.max_distinct_values ?? 1000}
              onChange={(e) =>
                handleChange(
                  'max_distinct_values',
                  e.target.value ? parseInt(e.target.value, 10) : null
                )
              }
              min={1}
              disabled={isLoading}
            />
          </FormField>
        </div>

        {/* Default Sample Ratio */}
        <div className="space-y-4 border-t border-surface-700/50 pt-4">
          <h4 className="text-sm font-medium text-slate-300">Sampling</h4>
          
          <FormField
            label="Default Sample Ratio"
            helperText="Default sampling ratio for tables (0.0 = no sampling, 1.0 = full data)"
            error={errors.default_sample_ratio}
          >
            <div className="space-y-2">
              <Slider
                value={profiling.default_sample_ratio ?? 1.0}
                onChange={(value) =>
                  handleChange('default_sample_ratio', typeof value === 'number' ? value : value[0])
                }
                min={0}
                max={1}
                step={0.01}
                showValue
                disabled={isLoading}
              />
              <Input
                type="number"
                value={profiling.default_sample_ratio ?? 1.0}
                onChange={(e) =>
                  handleChange(
                    'default_sample_ratio',
                    e.target.value ? parseFloat(e.target.value) : null
                  )
                }
                min={0}
                max={1}
                step={0.01}
                disabled={isLoading}
                className="w-32"
              />
            </div>
          </FormField>
        </div>

        {/* Enrichment Options */}
        <div className="space-y-4 border-t border-surface-700/50 pt-4">
          <h4 className="text-sm font-medium text-slate-300">Enrichment Options</h4>
          
          <FormField
            label="Enable Enrichment"
            helperText="Enable profiling enrichment features"
          >
            <Toggle
              checked={profiling.enable_enrichment ?? true}
              onChange={(checked) => handleChange('enable_enrichment', checked)}
              disabled={isLoading}
            />
          </FormField>

          {profiling.enable_enrichment !== false && (
            <>
              <FormField
                label="Enable Approximate Distinct"
                helperText="Use approximate distinct count for better performance"
              >
                <Toggle
                  checked={profiling.enable_approx_distinct ?? true}
                  onChange={(checked) => handleChange('enable_approx_distinct', checked)}
                  disabled={isLoading}
                />
              </FormField>

              <FormField
                label="Enable Schema Tracking"
                helperText="Track schema changes over time"
              >
                <Toggle
                  checked={profiling.enable_schema_tracking ?? true}
                  onChange={(checked) => handleChange('enable_schema_tracking', checked)}
                  disabled={isLoading}
                />
              </FormField>

              <FormField
                label="Enable Type Inference"
                helperText="Infer semantic data types"
              >
                <Toggle
                  checked={profiling.enable_type_inference ?? true}
                  onChange={(checked) => handleChange('enable_type_inference', checked)}
                  disabled={isLoading}
                />
              </FormField>

              <FormField
                label="Enable Column Stability"
                helperText="Track column stability over time"
              >
                <Toggle
                  checked={profiling.enable_column_stability ?? true}
                  onChange={(checked) => handleChange('enable_column_stability', checked)}
                  disabled={isLoading}
                />
              </FormField>
            </>
          )}
        </div>

        {/* Stability Configuration */}
        {profiling.enable_column_stability !== false && (
          <div className="space-y-4 border-t border-surface-700/50 pt-4">
            <h4 className="text-sm font-medium text-slate-300">Stability Configuration</h4>
            
            <FormField
              label="Stability Window (days)"
              helperText="Number of days to consider for stability calculation"
              error={errors.stability_window}
            >
              <Input
                type="number"
                value={profiling.stability_window ?? 7}
                onChange={(e) =>
                  handleChange(
                    'stability_window',
                    e.target.value ? parseInt(e.target.value, 10) : null
                  )
                }
                min={1}
                disabled={isLoading}
              />
            </FormField>
          </div>
        )}

        {/* Type Inference Configuration */}
        {profiling.enable_type_inference !== false && (
          <div className="space-y-4 border-t border-surface-700/50 pt-4">
            <h4 className="text-sm font-medium text-slate-300">Type Inference Configuration</h4>
            
            <FormField
              label="Type Inference Sample Size"
              helperText="Number of rows to sample for type inference"
              error={errors.type_inference_sample_size}
            >
              <Input
                type="number"
                value={profiling.type_inference_sample_size ?? 1000}
                onChange={(e) =>
                  handleChange(
                    'type_inference_sample_size',
                    e.target.value ? parseInt(e.target.value, 10) : null
                  )
                }
                min={1}
                disabled={isLoading}
              />
            </FormField>
          </div>
        )}

        {/* Lineage Extraction */}
        <div className="space-y-4 border-t border-surface-700/50 pt-4">
          <h4 className="text-sm font-medium text-slate-300">Lineage</h4>
          
          <FormField
            label="Extract Lineage"
            helperText="Extract data lineage information during profiling"
          >
            <Toggle
              checked={profiling.extract_lineage ?? false}
              onChange={(checked) => handleChange('extract_lineage', checked)}
              disabled={isLoading}
            />
          </FormField>
        </div>
      </div>
    </Card>
  )
}

