'use client'

import { useQuery } from '@tanstack/react-query'
import { FileText, Folder, Loader2, AlertCircle } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { listDatasetFiles } from '@/lib/api/datasets'
import { DatasetFileInfo } from '@/types/config'

export interface DatasetFileBrowserProps {
  onFileSelect?: (file: DatasetFileInfo) => void
  selectedFile?: string
}

export function DatasetFileBrowser({ onFileSelect, selectedFile }: DatasetFileBrowserProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-files'],
    queryFn: listDatasetFiles,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <div className="p-4 text-center">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-sm text-slate-400">
            {error instanceof Error ? error.message : 'Failed to load files'}
          </p>
        </div>
      </Card>
    )
  }

  const files = data?.files || []

  return (
    <Card>
      <div className="p-4">
        <h3 className="text-sm font-medium text-white mb-3">Dataset Files</h3>
        {files.length > 0 ? (
          <div className="space-y-1">
            {files.map((file) => (
              <button
                key={file.path}
                onClick={() => onFileSelect?.(file)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  selectedFile === file.path
                    ? 'bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800/40'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span className="truncate">{file.path}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-sm">
            <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No dataset files found</p>
          </div>
        )}
      </div>
    </Card>
  )
}

