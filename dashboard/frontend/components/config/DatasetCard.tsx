'use client'

import Link from 'next/link'
import { Database, FileText, BarChart3, TrendingUp, Shield, AlertTriangle, Columns } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { DatasetListItem } from '@/types/config'

export interface DatasetCardProps {
  dataset: DatasetListItem
}

export function DatasetCard({ dataset }: DatasetCardProps) {
  const identifier = [
    dataset.database,
    dataset.schema,
    dataset.table,
  ].filter(Boolean).join('.')

  const features = []
  if (dataset.has_profiling) features.push({ name: 'Profiling', icon: BarChart3, color: 'cyan' })
  if (dataset.has_drift) features.push({ name: 'Drift', icon: TrendingUp, color: 'amber' })
  if (dataset.has_validation) features.push({ name: 'Validation', icon: Shield, color: 'emerald' })
  if (dataset.has_anomaly) features.push({ name: 'Anomaly', icon: AlertTriangle, color: 'rose' })
  if (dataset.has_columns) features.push({ name: 'Columns', icon: Columns, color: 'purple' })

  return (
    <Link href={`/config/datasets/${encodeURIComponent(dataset.dataset_id)}`}>
      <Card hover className="h-full">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Database className="w-5 h-5 text-slate-400 flex-shrink-0" />
                <h3 className="text-lg font-semibold text-white truncate">
                  {identifier || 'Unnamed Dataset'}
                </h3>
              </div>
              {dataset.source_file && (
                <div className="flex items-center gap-1.5 text-sm text-slate-400 mt-1">
                  <FileText className="w-3.5 h-3.5" />
                  <span className="truncate">{dataset.source_file}</span>
                </div>
              )}
            </div>
          </div>

          {/* Features */}
          {features.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {features.map((feature) => {
                const Icon = feature.icon
                // Map colors to valid Badge variants
                const variantMap: Record<string, 'info' | 'success' | 'warning' | 'error' | 'default'> = {
                  cyan: 'info',
                  emerald: 'success',
                  amber: 'warning',
                  rose: 'error',
                  purple: 'info',
                }
                return (
                  <Badge
                    key={feature.name}
                    variant={variantMap[feature.color] || 'default'}
                    outline
                  >
                    <Icon className="w-3 h-3 mr-1" />
                    {feature.name}
                  </Badge>
                )
              })}
            </div>
          ) : (
            <div className="text-sm text-slate-500 italic">
              No features configured
            </div>
          )}
        </div>
      </Card>
    </Link>
  )
}

