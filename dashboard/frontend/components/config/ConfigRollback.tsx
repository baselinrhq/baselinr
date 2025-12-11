'use client'

import { useState } from 'react'
import { AlertTriangle, RotateCcw, Loader2 } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormField } from '@/components/ui/FormField'
import { ConfigVersionResponse } from '@/types/config'

export interface ConfigRollbackProps {
  versionId: string
  versionData: ConfigVersionResponse
  onConfirm: (comment?: string) => Promise<void>
  onCancel: () => void
  isOpen: boolean
}

export function ConfigRollback({
  versionId,
  versionData,
  onConfirm,
  onCancel,
  isOpen,
}: ConfigRollbackProps) {
  const [comment, setComment] = useState('')
  const [isRestoring, setIsRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    setIsRestoring(true)
    setError(null)
    
    try {
      await onConfirm(comment || undefined)
      // Reset form on success
      setComment('')
      setIsRestoring(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore configuration')
      setIsRestoring(false)
    }
  }

  const handleCancel = () => {
    setComment('')
    setError(null)
    onCancel()
  }

  const createdAt = new Date(versionData.created_at)
  const timeAgo = new Date().getTime() - createdAt.getTime()
  const daysAgo = Math.floor(timeAgo / (1000 * 60 * 60 * 24))

  return (
    <Modal isOpen={isOpen} onClose={handleCancel} title="Restore Configuration Version">
      <div className="space-y-4">
        {/* Warning */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-yellow-900 mb-1">
                Restore Configuration Version
              </h4>
              <p className="text-sm text-yellow-800">
                This will replace your current configuration with the version from{' '}
                {createdAt.toLocaleString()}. This action cannot be undone, but a new history
                entry will be created for the restore.
              </p>
            </div>
          </div>
        </div>

        {/* Version Info */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Version Details</h4>
          <div className="space-y-1 text-sm text-gray-600">
            <div>
              <span className="font-medium">Version ID:</span>{' '}
              <code className="bg-gray-100 px-1 rounded text-xs">{versionId.substring(0, 8)}...</code>
            </div>
            <div>
              <span className="font-medium">Created:</span> {createdAt.toLocaleString()}
              {daysAgo > 0 && <span className="text-gray-500"> ({daysAgo} day{daysAgo !== 1 ? 's' : ''} ago)</span>}
            </div>
            {versionData.created_by && (
              <div>
                <span className="font-medium">Created by:</span> {versionData.created_by}
              </div>
            )}
            {versionData.comment && (
              <div>
                <span className="font-medium">Original comment:</span> {versionData.comment}
              </div>
            )}
          </div>
        </div>

        {/* Comment Input */}
        <FormField
          label="Restore Comment (Optional)"
          helperText="Add a comment to describe why you're restoring this version"
        >
          <Input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="e.g., Rolling back due to connection issues"
            disabled={isRestoring}
          />
        </FormField>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <Button
            variant="secondary"
            onClick={handleCancel}
            disabled={isRestoring}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isRestoring}
            icon={isRestoring ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
          >
            {isRestoring ? 'Restoring...' : 'Restore Configuration'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ConfigRollback

