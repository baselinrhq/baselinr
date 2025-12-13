'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Loader2, AlertCircle, CheckCircle, XCircle, X, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ConnectionCard } from '@/components/config/ConnectionCard'
import { ConnectionWizard } from '@/components/config/ConnectionWizard'
import {
  listConnections,
  getConnection,
  saveConnection,
  updateConnection,
  deleteConnection,
  testConnection,
} from '@/lib/api/connections'
import { SavedConnection, ConnectionsListResponse } from '@/types/connection'
import { ConnectionConfig } from '@/types/config'
import { useConfig } from '@/hooks/useConfig'

export default function ConnectionsPage() {
  const queryClient = useQueryClient()
  const { updateConfigPath } = useConfig()
  
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editingConnectionId, setEditingConnectionId] = useState<string | undefined>()
  const [editingConnection, setEditingConnection] = useState<ConnectionConfig | undefined>()
  const [notification, setNotification] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  // Fetch connections
  const {
    data: connectionsData,
    isLoading,
    error,
  } = useQuery<ConnectionsListResponse>({
    queryKey: ['connections'],
    queryFn: listConnections,
    retry: false, // Don't retry on 404 - backend not implemented yet
  })

  // Save connection mutation
  const saveMutation = useMutation({
    mutationFn: async ({ name, connection }: { name: string; connection: ConnectionConfig }) => {
      if (editingConnectionId) {
        return updateConnection(editingConnectionId, name, connection)
      }
      return saveConnection(name, connection)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      setWizardOpen(false)
      setEditingConnectionId(undefined)
    },
  })

  // Delete connection mutation
  const deleteMutation = useMutation({
    mutationFn: deleteConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
    },
  })

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: async (connection: ConnectionConfig) => {
      return testConnection(connection)
    },
  })

  const handleNewConnection = () => {
    setEditingConnectionId(undefined)
    setWizardOpen(true)
  }

  const handleEdit = async (id: string) => {
    try {
      const connection = await getConnection(id)
      setEditingConnectionId(id)
      setEditingConnection(connection.connection)
      setWizardOpen(true)
    } catch (err) {
      console.error('Failed to load connection:', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this connection?')) {
      try {
        await deleteMutation.mutateAsync(id)
        setNotification({
          type: 'success',
          message: 'Connection deleted successfully',
        })
      } catch (err) {
        console.error('Failed to delete connection:', err)
        setNotification({
          type: 'error',
          message: 'Failed to delete connection. Please try again.',
        })
      }
    }
  }

  const handleTest = async (id: string) => {
    try {
      const connection = await getConnection(id)
      await testMutation.mutateAsync(connection.connection)
      setNotification({
        type: 'success',
        message: 'Connection test successful!',
      })
    } catch (err) {
      console.error('Connection test failed:', err)
      setNotification({
        type: 'error',
        message: `Connection test failed: ${err instanceof Error ? err.message : 'Unknown error'}`,
      })
    }
  }

  const handleUseAsSource = async (id: string) => {
    if (confirm('Set this connection as the source connection in the main configuration?')) {
      try {
        const connection = await getConnection(id)
        updateConfigPath(['source'], connection.connection)
        setNotification({
          type: 'success',
          message: 'Source connection updated successfully!',
        })
      } catch (err) {
        console.error('Failed to set source connection:', err)
        setNotification({
          type: 'error',
          message: 'Failed to set source connection. Please try again.',
        })
      }
    }
  }

  const handleWizardSave = async (savedConnection: SavedConnection) => {
    // The wizard passes a SavedConnection, but we need to extract name and connection
    await saveMutation.mutateAsync({
      name: savedConnection.name,
      connection: savedConnection.connection,
    })
  }

  const connections = connectionsData?.connections || []

  // Auto-dismiss notification after 5 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        setNotification(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Notification Toast */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 glass-card border ${
            notification.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10'
              : 'border-rose-500/30 bg-rose-500/10'
          } p-4 flex items-start gap-3 shadow-lg min-w-[300px] max-w-md animate-in slide-in-from-top-5`}
        >
          {notification.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div
              className={`font-medium ${
                notification.type === 'success' ? 'text-emerald-300' : 'text-rose-300'
              }`}
            >
              {notification.type === 'success' ? 'Success' : 'Error'}
            </div>
            <div
              className={`text-sm mt-1 ${
                notification.type === 'success' ? 'text-emerald-400/80' : 'text-rose-400/80'
              }`}
            >
              {notification.message}
            </div>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/config" className="hover:text-cyan-400">
              Configuration
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white font-medium">Connections</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Database Connections</h1>
          <p className="text-slate-400 mt-1">
            Manage your database connections for data profiling
          </p>
        </div>
        <Button
          onClick={handleNewConnection}
          icon={<Plus className="w-4 h-4" />}
        >
          New Connection
        </Button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="glass-card border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-medium text-amber-300">Connection Error</div>
            <div className="text-sm text-amber-400/80 mt-1">
              {error instanceof Error ? (
                error.message.includes('NetworkError') || error.message.includes('Failed to fetch') ? (
                  <>
                    Unable to connect to the backend API. Please ensure:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>The backend server is running on <code className="bg-amber-500/10 px-1 rounded text-amber-300">http://localhost:8000</code></li>
                      <li>Check the browser console for more details</li>
                      <li>Verify CORS settings if running on a different port</li>
                    </ul>
                  </>
                ) : error.message.includes('Not Found') ? (
                  <>
                    The API endpoint was not found. This may indicate the backend routes are not properly registered.
                    Check that the backend server is running and includes the connection routes from Plan 23.
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

      {/* Empty State - Show even with error to allow testing wizard */}
      {!isLoading && connections.length === 0 && (
        <div className="glass-card p-12 text-center">
          <div className="text-slate-500 mb-4">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">
            No connections yet
          </h3>
          <p className="text-slate-400 mb-6">
            Create your first database connection to get started
          </p>
          <Button onClick={handleNewConnection} icon={<Plus className="w-4 h-4" />}>
            New Connection
          </Button>
        </div>
      )}

      {/* Connections Grid */}
      {!isLoading && connections.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {connections.map((connection) => (
            <ConnectionCard
              key={connection.id}
              connection={connection}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onTest={handleTest}
              onUseAsSource={handleUseAsSource}
            />
          ))}
        </div>
      )}

      {/* Connection Wizard */}
      <ConnectionWizard
        isOpen={wizardOpen}
        onClose={() => {
          setWizardOpen(false)
          setEditingConnectionId(undefined)
          setEditingConnection(undefined)
        }}
        onSave={handleWizardSave}
        initialConnection={editingConnection}
        connectionId={editingConnectionId}
      />
    </div>
  )
}

