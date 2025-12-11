'use client'

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { ConfigVersionResponse } from '@/types/config'
import { toYAML } from '@/lib/utils/yaml'
import { maskSensitiveConfig } from '@/lib/utils/sanitize'
import dynamic from 'next/dynamic'

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

export interface ConfigVersionViewProps {
  versionData: ConfigVersionResponse
  onClose: () => void
  isOpen: boolean
}

export function ConfigVersionView({
  versionData,
  onClose,
  isOpen,
}: ConfigVersionViewProps) {
  const [viewMode, setViewMode] = useState<'json' | 'yaml'>('json')
  const [copied, setCopied] = useState(false)
  const [showSensitive, setShowSensitive] = useState(false)

  // Mask sensitive data for display
  const displayConfig = showSensitive 
    ? versionData.config 
    : (maskSensitiveConfig(versionData.config, false) as typeof versionData.config)

  const configJson = JSON.stringify(displayConfig, null, 2)
  const configYaml = viewMode === 'yaml' ? toYAML(displayConfig) : ''

  const handleCopy = async () => {
    const textToCopy = viewMode === 'json' ? configJson : configYaml
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const createdAt = new Date(versionData.created_at)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Configuration Version Details"
      size="xl"
    >
      <div className="space-y-4">
        {/* Version Info */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">Version ID:</span>
              <div className="mt-1 font-mono text-xs text-gray-900 break-all">
                {versionData.version_id}
              </div>
            </div>
            <div>
              <span className="font-medium text-gray-700">Created:</span>
              <div className="mt-1 text-gray-900">
                {createdAt.toLocaleString()}
              </div>
            </div>
            {versionData.created_by && (
              <div>
                <span className="font-medium text-gray-700">Created by:</span>
                <div className="mt-1 text-gray-900">{versionData.created_by}</div>
              </div>
            )}
            {versionData.comment && (
              <div className="col-span-2">
                <span className="font-medium text-gray-700">Comment:</span>
                <div className="mt-1 text-gray-900">{versionData.comment}</div>
              </div>
            )}
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('json')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === 'json'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              JSON
            </button>
            <button
              onClick={() => setViewMode('yaml')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === 'yaml'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              YAML
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSensitive(!showSensitive)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
            >
              {showSensitive ? 'Hide' : 'Show'} Sensitive
            </button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              icon={copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            >
              {copied ? 'Copied!' : 'Copy'}
            </Button>
          </div>
        </div>

        {/* Config Display */}
        <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: '500px' }}>
          {viewMode === 'json' ? (
            <MonacoEditor
              height="500px"
              language="json"
              value={configJson}
              theme="vs-light"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                wordWrap: 'on',
              }}
            />
          ) : (
            <MonacoEditor
              height="500px"
              language="yaml"
              value={configYaml}
              theme="vs-light"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                wordWrap: 'on',
              }}
            />
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ConfigVersionView

