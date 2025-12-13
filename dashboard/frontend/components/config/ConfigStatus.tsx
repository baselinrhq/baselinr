'use client'

import { RefreshCw, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { BaselinrConfig, ConfigSectionStatus } from '@/types/config'
import Link from 'next/link'

export interface ConfigStatusProps {
  config?: BaselinrConfig | null
  isLoading?: boolean
  onRefresh?: () => void
}

/**
 * Check the status of a configuration section
 */
function checkSectionStatus(
  section: string,
  config: BaselinrConfig | null | undefined
): ConfigSectionStatus {
  if (!config) {
    return {
      section,
      status: 'not_configured',
      message: 'Configuration not loaded',
    }
  }

  switch (section) {
    case 'connections':
      // Check if source connection exists and has required fields
      if (!config.source) {
        return {
          section,
          status: 'not_configured',
          message: 'Source connection not configured',
        }
      }
      if (!config.source.type || !config.source.database) {
        return {
          section,
          status: 'incomplete',
          message: 'Source connection missing required fields',
        }
      }
      return {
        section,
        status: 'configured',
        message: 'Source connection configured',
      }

    case 'storage':
      // Check if storage config exists with connection and table names
      if (!config.storage) {
        return {
          section,
          status: 'not_configured',
          message: 'Storage configuration not set',
        }
      }
      if (!config.storage.connection) {
        return {
          section,
          status: 'incomplete',
          message: 'Storage connection not configured',
        }
      }
      if (!config.storage.results_table || !config.storage.runs_table) {
        return {
          section,
          status: 'incomplete',
          message: 'Storage table names not configured',
        }
      }
      return {
        section,
        status: 'configured',
        message: 'Storage fully configured',
      }

    case 'tables':
      // Check if profiling tables exist and have at least one pattern
      if (!config.profiling) {
        return {
          section,
          status: 'not_configured',
          message: 'Profiling configuration not set',
        }
      }
      const tables = config.profiling.tables
      if (!tables || tables.length === 0) {
        return {
          section,
          status: 'not_configured',
          message: 'No table patterns configured',
        }
      }
      return {
        section,
        status: 'configured',
        message: `${tables.length} table pattern(s) configured`,
      }

    case 'profiling':
      // Check if profiling config exists
      if (!config.profiling) {
        return {
          section,
          status: 'not_configured',
          message: 'Profiling configuration not set',
        }
      }
      return {
        section,
        status: 'configured',
        message: 'Profiling configuration exists',
      }

    case 'validation':
      // Validation rules are optional, so just check if config exists
      if (!config.validation) {
        return {
          section,
          status: 'not_configured',
          message: 'Validation configuration not set',
        }
      }
      const rules = config.validation.rules
      if (!rules || rules.length === 0) {
        return {
          section,
          status: 'not_configured',
          message: 'No validation rules configured',
        }
      }
      return {
        section,
        status: 'configured',
        message: `${rules.length} validation rule(s) configured`,
      }

    case 'drift':
      // Check if drift detection config exists
      if (!config.drift_detection) {
        return {
          section,
          status: 'not_configured',
          message: 'Drift detection not configured',
        }
      }
      return {
        section,
        status: 'configured',
        message: 'Drift detection configured',
      }

    case 'anomaly':
      // Check if anomaly detection config exists
      // Note: anomaly_detection might be in storage config or separate
      if (!config.storage?.enable_anomaly_detection) {
        return {
          section,
          status: 'not_configured',
          message: 'Anomaly detection not enabled',
        }
      }
      return {
        section,
        status: 'configured',
        message: 'Anomaly detection enabled',
      }

    case 'hooks':
      // Check if hooks config exists
      if (!config.hooks) {
        return {
          section,
          status: 'not_configured',
          message: 'Alert hooks not configured',
        }
      }
      const hooks = config.hooks.hooks
      if (!hooks || hooks.length === 0) {
        return {
          section,
          status: 'not_configured',
          message: 'No alert hooks configured',
        }
      }
      return {
        section,
        status: 'configured',
        message: `${hooks.length} alert hook(s) configured`,
      }

    default:
      return {
        section,
        status: 'not_configured',
        message: 'Unknown section',
      }
  }
}

/**
 * Get all section statuses and calculate overall completion
 */
function getConfigStatus(config: BaselinrConfig | null | undefined): {
  sections: ConfigSectionStatus[]
  overall_completion: number
  configured_sections: number
  total_sections: number
} {
  const sectionNames = [
    'connections',
    'storage',
    'tables',
    'profiling',
    'validation',
    'drift',
    'anomaly',
    'hooks',
  ]

  const sections = sectionNames.map((name) => checkSectionStatus(name, config))
  const configured_sections = sections.filter((s) => s.status === 'configured').length
  const total_sections = sections.length
  const overall_completion = Math.round((configured_sections / total_sections) * 100)

  return {
    sections,
    overall_completion,
    configured_sections,
    total_sections,
  }
}

/**
 * Get status badge variant
 */
function getStatusBadge(status: ConfigSectionStatus['status']) {
  switch (status) {
    case 'configured':
      return (
        <Badge variant="success" icon={<CheckCircle className="w-3 h-3" />}>
          Configured
        </Badge>
      )
    case 'incomplete':
      return (
        <Badge variant="warning" icon={<AlertCircle className="w-3 h-3" />}>
          Incomplete
        </Badge>
      )
    case 'error':
      return (
        <Badge variant="error" icon={<XCircle className="w-3 h-3" />}>
          Error
        </Badge>
      )
    case 'not_configured':
    default:
      return (
        <Badge variant="default" icon={<XCircle className="w-3 h-3" />}>
          Not Configured
        </Badge>
      )
  }
}

/**
 * Get section route
 */
function getSectionRoute(section: string): string {
  const routes: Record<string, string> = {
    connections: '/config/connections',
    storage: '/config/storage',
    tables: '/config/tables',
    profiling: '/config/profiling',
    validation: '/config/validation',
    drift: '/config/drift',
    anomaly: '/config/anomaly',
    hooks: '/config/hooks',
  }
  return routes[section] || '/config'
}

/**
 * Get section display name
 */
function getSectionName(section: string): string {
  const names: Record<string, string> = {
    connections: 'Connections',
    storage: 'Storage',
    tables: 'Tables',
    profiling: 'Profiling',
    validation: 'Validation Rules',
    drift: 'Drift Detection',
    anomaly: 'Anomaly Detection',
    hooks: 'Alert Hooks',
  }
  return names[section] || section
}

export function ConfigStatus({ config, isLoading = false, onRefresh }: ConfigStatusProps) {
  const status = getConfigStatus(config)

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Configuration Status</h3>
        {onRefresh && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </Button>
        )}
      </div>

      {isLoading && !config && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
          <span className="ml-2 text-sm text-slate-400">Loading configuration...</span>
        </div>
      )}

      {!isLoading && (
        <>
          {/* Overall Completion */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-300">Overall Completion</span>
              <span className="text-sm font-bold text-white">
                {status.overall_completion}%
              </span>
            </div>
            <div className="w-full bg-surface-700 rounded-full h-2.5">
              <div
                className="bg-cyan-500 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${status.overall_completion}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {status.configured_sections} of {status.total_sections} sections configured
            </p>
          </div>

          {/* Section Status List */}
          <div className="space-y-3">
            {status.sections.map((sectionStatus) => (
              <div
                key={sectionStatus.section}
                className="flex items-center justify-between py-2 border-b border-surface-700/50 last:border-0"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Link
                      href={getSectionRoute(sectionStatus.section)}
                      className="text-sm font-medium text-white hover:text-cyan-400 transition-colors"
                    >
                      {getSectionName(sectionStatus.section)}
                    </Link>
                  </div>
                  {sectionStatus.message && (
                    <p className="mt-0.5 text-xs text-slate-400">{sectionStatus.message}</p>
                  )}
                </div>
                <div className="ml-4">{getStatusBadge(sectionStatus.status)}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}

export default ConfigStatus

