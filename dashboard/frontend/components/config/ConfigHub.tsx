'use client'

import Link from 'next/link'
import {
  HardDrive,
  Table,
  BarChart3,
  Shield,
  TrendingUp,
  Bell,
  ArrowRight,
  Database,
  Eye,
} from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { BaselinrConfig, ConfigSectionStatus } from '@/types/config'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export interface ConfigHubProps {
  config?: BaselinrConfig | null
  isLoading?: boolean
}

interface ConfigSection {
  id: string
  name: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

const configSections: ConfigSection[] = [
  {
    id: 'connections',
    name: 'Connections',
    description: 'Configure database connections for data profiling',
    href: '/config/connections',
    icon: Database,
  },
  {
    id: 'storage',
    name: 'Storage',
    description: 'Configure storage database and table names',
    href: '/config/storage',
    icon: HardDrive,
  },
  {
    id: 'tables',
    name: 'Tables',
    description: 'Select tables to profile with pattern matching',
    href: '/config/tables',
    icon: Table,
  },
  {
    id: 'profiling',
    name: 'Profiling',
    description: 'Configure profiling settings and metrics',
    href: '/config/profiling',
    icon: BarChart3,
  },
  {
    id: 'validation',
    name: 'Validation Rules',
    description: 'Create and manage data validation rules',
    href: '/config/validation',
    icon: Shield,
  },
  {
    id: 'drift',
    name: 'Drift Detection',
    description: 'Configure drift detection strategies and thresholds',
    href: '/config/drift',
    icon: TrendingUp,
  },
  {
    id: 'anomaly',
    name: 'Anomaly Detection',
    description: 'Configure anomaly detection and expectation learning',
    href: '/config/anomaly',
    icon: Eye,
  },
  {
    id: 'hooks',
    name: 'Alert Hooks',
    description: 'Configure alert hooks (Slack, SQL, logging, custom)',
    href: '/config/hooks',
    icon: Bell,
  },
]

/**
 * Check the status of a configuration section
 */
function checkSectionStatus(
  section: string,
  config: BaselinrConfig | null | undefined
): ConfigSectionStatus['status'] {
  if (!config) {
    return 'not_configured'
  }

  switch (section) {
    case 'connections':
      if (!config.source || !config.source.type || !config.source.database) {
        return 'not_configured'
      }
      return 'configured'

    case 'storage':
      if (!config.storage || !config.storage.connection) {
        return 'not_configured'
      }
      if (!config.storage.results_table || !config.storage.runs_table) {
        return 'incomplete'
      }
      return 'configured'

    case 'tables':
      if (!config.profiling || !config.profiling.tables || config.profiling.tables.length === 0) {
        return 'not_configured'
      }
      return 'configured'

    case 'profiling':
      if (!config.profiling) {
        return 'not_configured'
      }
      return 'configured'

    case 'validation':
      if (!config.validation) {
        return 'not_configured'
      }
      if (!config.validation.rules || config.validation.rules.length === 0) {
        return 'not_configured'
      }
      return 'configured'

    case 'drift':
      if (!config.drift_detection) {
        return 'not_configured'
      }
      return 'configured'

    case 'anomaly':
      if (!config.storage?.enable_anomaly_detection) {
        return 'not_configured'
      }
      return 'configured'

    case 'hooks':
      if (!config.hooks || !config.hooks.hooks || config.hooks.hooks.length === 0) {
        return 'not_configured'
      }
      return 'configured'

    default:
      return 'not_configured'
  }
}

/**
 * Get status badge for a section
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
    case 'not_configured':
    default:
      return (
        <Badge variant="default" icon={<XCircle className="w-3 h-3" />}>
          Not Configured
        </Badge>
      )
  }
}

export function ConfigHub({ config }: ConfigHubProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white mb-1">Configuration Sections</h2>
        <p className="text-sm text-slate-400">
          Manage your Baselinr configuration across all sections
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {configSections.map((section) => {
          const Icon = section.icon
          const status = checkSectionStatus(section.id, config)

          return (
            <Link key={section.id} href={section.href}>
              <Card hover className="h-full">
                <div className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-surface-700/50 rounded-lg">
                        <Icon className="w-5 h-5 text-accent-400" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-white">
                          {section.name}
                        </h3>
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-slate-400 mb-4">{section.description}</p>

                  <div className="flex items-center justify-between">
                    {getStatusBadge(status)}
                    <ArrowRight className="w-4 h-4 text-slate-500" />
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

export default ConfigHub
