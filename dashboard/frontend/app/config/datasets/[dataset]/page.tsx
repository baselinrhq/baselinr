'use client'

import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Loader2, AlertCircle, Database } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { DatasetDetail } from '@/components/config/DatasetDetail'
import { getDataset } from '@/lib/api/datasets'

// Enable dynamic params for static export (client-side rendering)
export const dynamicParams = true

export default function DatasetDetailPage() {
  const params = useParams()
  const router = useRouter()
  const datasetId = decodeURIComponent(params.dataset as string)

  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => getDataset(datasetId),
    enabled: !!datasetId,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm text-slate-400">Loading dataset...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6 lg:p-8">
        <Card>
          <div className="p-12 text-center">
            <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">
              Dataset Not Found
            </h3>
            <p className="text-sm text-slate-400 mb-6">
              {error instanceof Error ? error.message : 'The requested dataset could not be found'}
            </p>
            <Button onClick={() => router.push('/config/datasets')} variant="outline">
              Back to Datasets
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  const identifier = [
    data.config.database,
    data.config.schema,
    data.config.table,
  ].filter(Boolean).join('.')

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <Link href="/config" className="hover:text-cyan-400">
            Configuration
          </Link>
          <ChevronRight className="w-4 h-4" />
          <Link href="/config/datasets" className="hover:text-cyan-400">
            Datasets
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-white font-medium">{identifier || 'Dataset'}</span>
        </div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Database className="w-6 h-6" />
          {identifier || 'Dataset Configuration'}
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure profiling, drift detection, validation, and anomaly detection for this dataset
        </p>
      </div>

      {/* Dataset Detail */}
      <DatasetDetail dataset={data} />
    </div>
  )
}

