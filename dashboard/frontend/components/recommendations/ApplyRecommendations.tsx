'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckCircle2, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Modal, ModalFooter } from '@/components/ui/Modal'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { applyRecommendations } from '@/lib/api/recommendations'
import type { ApplyRecommendationsRequest } from '@/types/recommendation'

interface ApplyRecommendationsProps {
  connectionId: string
  selectedTables: Array<{ schema: string; table: string; database?: string }>
  onClose: () => void
  onSuccess: () => void
}

export default function ApplyRecommendations({
  connectionId,
  selectedTables,
  onClose,
  onSuccess,
}: ApplyRecommendationsProps) {
  const [comment, setComment] = useState('')

  const mutation = useMutation({
    mutationFn: (request: ApplyRecommendationsRequest) => applyRecommendations(request),
    onSuccess: () => {
      onSuccess()
    },
  })

  const handleApply = () => {
    const request: ApplyRecommendationsRequest = {
      connection_id: connectionId,
      selected_tables: selectedTables,
      comment: comment || undefined,
    }

    mutation.mutate(request)
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Apply Recommendations"
      size="lg"
    >
      <div className="space-y-4">
        {mutation.isError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex items-center gap-2">
              <X className="w-5 h-5 text-red-600" />
              <div>
                <div className="font-semibold text-red-900">Error</div>
                <div className="text-sm text-red-700">
                  {mutation.error instanceof Error
                    ? mutation.error.message
                    : 'Failed to apply recommendations'}
                </div>
              </div>
            </div>
          </div>
        )}

        {mutation.isSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <div>
                <div className="font-semibold text-green-900">Success</div>
                <div className="text-sm text-green-700">
                  {mutation.data?.message || 'Recommendations applied successfully'}
                </div>
              </div>
            </div>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            Selected Tables ({selectedTables.length})
          </h3>
          <div className="bg-gray-50 rounded-md p-4 max-h-64 overflow-y-auto">
            <ul className="space-y-1">
              {selectedTables.map((table, idx) => (
                <li key={idx} className="text-sm text-gray-700">
                  {table.schema && <span className="text-gray-500">{table.schema}.</span>}
                  {table.table}
                  {table.database && (
                    <span className="text-gray-500 ml-2">({table.database})</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Comment (optional)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add a comment for this configuration change..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="text-sm text-blue-900">
            <strong>Note:</strong> This will add the selected tables to your configuration file.
            Column-level checks can be configured separately after applying.
          </div>
        </div>
      </div>

      <ModalFooter>
        <Button onClick={onClose} variant="secondary" disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button
          onClick={handleApply}
          variant="primary"
          disabled={mutation.isPending || mutation.isSuccess}
        >
          {mutation.isPending ? (
            <>
              <LoadingSpinner size="sm" className="mr-2" />
              Applying...
            </>
          ) : mutation.isSuccess ? (
            <>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Applied
            </>
          ) : (
            'Apply Recommendations'
          )}
        </Button>
      </ModalFooter>
    </Modal>
  )
}


