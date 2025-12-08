'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Loader2, AlertCircle, Bell } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Toggle } from '@/components/ui/Toggle'
import { HookList } from '@/components/config/HookList'
import { HookWizard } from '@/components/config/HookWizard'
import {
  fetchHooks,
  fetchHook,
  createHook,
  updateHook,
  deleteHook,
  setHooksEnabled,
} from '@/lib/api/hooks'
import { HooksListResponse } from '@/types/hook'
import { HookConfig } from '@/types/config'

export default function HooksPage() {
  const queryClient = useQueryClient()
  
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editingHookId, setEditingHookId] = useState<string | undefined>()
  const [editingHook, setEditingHook] = useState<HookConfig | undefined>()

  // Fetch hooks
  const {
    data: hooksData,
    isLoading,
    error,
  } = useQuery<HooksListResponse>({
    queryKey: ['hooks'],
    queryFn: fetchHooks,
    retry: false,
  })

  // Toggle hooks enabled mutation
  const toggleEnabledMutation = useMutation({
    mutationFn: setHooksEnabled,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hooks'] })
    },
  })

  // Save hook mutation
  const saveMutation = useMutation({
    mutationFn: async (hook: HookConfig) => {
      if (editingHookId) {
        return updateHook(editingHookId, hook)
      }
      return createHook(hook)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hooks'] })
      setWizardOpen(false)
      setEditingHookId(undefined)
      setEditingHook(undefined)
    },
  })

  // Delete hook mutation
  const deleteMutation = useMutation({
    mutationFn: deleteHook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hooks'] })
    },
  })

  const handleNewHook = () => {
    setEditingHookId(undefined)
    setEditingHook(undefined)
    setWizardOpen(true)
  }

  const handleEdit = async (id: string) => {
    try {
      const hookData = await fetchHook(id)
      setEditingHookId(id)
      setEditingHook(hookData.hook)
      setWizardOpen(true)
    } catch (err) {
      console.error('Failed to load hook:', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this hook?')) {
      try {
        await deleteMutation.mutateAsync(id)
      } catch (err) {
        console.error('Failed to delete hook:', err)
        alert('Failed to delete hook. Please try again.')
      }
    }
  }

  const handleToggleEnabled = async (enabled: boolean) => {
    try {
      await toggleEnabledMutation.mutateAsync(enabled)
    } catch (err) {
      console.error('Failed to toggle hooks enabled:', err)
      alert('Failed to update hooks status. Please try again.')
    }
  }

  const handleWizardSave = async (hook: HookConfig) => {
    await saveMutation.mutateAsync(hook)
  }

  const hooks = hooksData?.hooks || []
  const hooksEnabled = hooksData?.hooks_enabled ?? true

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alert Hooks</h1>
          <p className="text-gray-600 mt-1">
            Configure alert hooks for drift detection, schema changes, and profiling events
          </p>
        </div>
        <Button
          onClick={handleNewHook}
          icon={<Plus className="w-4 h-4" />}
        >
          New Hook
        </Button>
      </div>

      {/* Master Toggle */}
      {!isLoading && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-gray-500" />
            <div>
              <div className="font-medium text-gray-900">Enable All Hooks</div>
              <div className="text-sm text-gray-600">
                Master switch to enable or disable all hooks globally
              </div>
            </div>
          </div>
          <Toggle
            checked={hooksEnabled}
            onChange={handleToggleEnabled}
            disabled={toggleEnabledMutation.isPending}
          />
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-medium text-yellow-900">Hooks Error</div>
            <div className="text-sm text-yellow-700 mt-1">
              {error instanceof Error ? (
                error.message.includes('NetworkError') || error.message.includes('Failed to fetch') ? (
                  <>
                    Unable to connect to the backend API. Please ensure:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>The backend server is running on <code className="bg-yellow-100 px-1 rounded">http://localhost:8000</code></li>
                      <li>Check the browser console for more details</li>
                      <li>Verify CORS settings if running on a different port</li>
                    </ul>
                  </>
                ) : (
                  error.message
                )
              ) : (
                'Unknown error occurred'
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && hooks.length === 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <Bell className="w-16 h-16 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No hooks configured yet
          </h3>
          <p className="text-gray-600 mb-6">
            Create your first alert hook to receive notifications about data drift and profiling events
          </p>
          <Button onClick={handleNewHook} icon={<Plus className="w-4 h-4" />}>
            New Hook
          </Button>
        </div>
      )}

      {/* Hooks List */}
      {!isLoading && hooks.length > 0 && (
        <HookList
          hooks={hooks}
          hooksEnabled={hooksEnabled}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}

      {/* Hook Wizard */}
      <HookWizard
        isOpen={wizardOpen}
        onClose={() => {
          setWizardOpen(false)
          setEditingHookId(undefined)
          setEditingHook(undefined)
        }}
        onSave={handleWizardSave}
        initialHook={editingHook}
        hookId={editingHookId}
      />
    </div>
  )
}

