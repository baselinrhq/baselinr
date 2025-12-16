'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { getDatasetFile, updateDatasetFile } from '@/lib/api/datasets'
import dynamic from 'next/dynamic'

// Dynamically import Monaco editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

export interface DatasetFileEditorProps {
  filePath?: string
  onClose?: () => void
}

export function DatasetFileEditor({ filePath, onClose }: DatasetFileEditorProps) {
  const [content, setContent] = useState('')
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['dataset-file', filePath],
    queryFn: () => filePath ? getDatasetFile(filePath) : null,
    enabled: !!filePath,
  })

  const saveMutation = useMutation({
    mutationFn: (newContent: string) => {
      if (!filePath) throw new Error('No file path')
      return updateDatasetFile(filePath, { content: newContent })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset-files'] })
      queryClient.invalidateQueries({ queryKey: ['dataset-file', filePath] })
    },
  })

  useEffect(() => {
    if (data?.content) {
      setContent(data.content)
    }
  }, [data])

  if (!filePath) {
    return (
      <Card>
        <div className="p-8 text-center text-slate-400">
          Select a file to edit
        </div>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <div className="p-8 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-cyan-400 mx-auto" />
        </div>
      </Card>
    )
  }

  return (
    <Card padding="none">
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-white">{filePath}</h3>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => saveMutation.mutate(content)}
            disabled={saveMutation.isPending}
            loading={saveMutation.isPending}
            icon={<Save className="w-4 h-4" />}
            size="sm"
          >
            Save
          </Button>
          {onClose && (
            <Button variant="outline" onClick={onClose} size="sm">
              Close
            </Button>
          )}
        </div>
      </div>
      <div className="h-[600px]">
        <MonacoEditor
          language="yaml"
          value={content}
          onChange={(value) => setContent(value || '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
          }}
        />
      </div>
    </Card>
  )
}

