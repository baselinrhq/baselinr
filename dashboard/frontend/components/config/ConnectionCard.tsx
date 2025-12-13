'use client'

import { useState } from 'react'
import { Edit, Trash2, TestTube, Database } from 'lucide-react'
import { SavedConnection } from '@/types/connection'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

export interface ConnectionCardProps {
  connection: SavedConnection
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTest: (id: string) => void
  onUseAsSource?: (id: string) => void
}

const DATABASE_TYPE_LABELS: Record<string, string> = {
  postgres: 'PostgreSQL',
  mysql: 'MySQL',
  redshift: 'Amazon Redshift',
  snowflake: 'Snowflake',
  bigquery: 'Google BigQuery',
  sqlite: 'SQLite',
}

export function ConnectionCard({
  connection,
  onEdit,
  onDelete,
  onTest,
  onUseAsSource,
}: ConnectionCardProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const handleDelete = () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true)
      return
    }
    setIsDeleting(true)
    onDelete(connection.id)
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return 'Invalid date'
    }
  }

  const getConnectionSummary = () => {
    const conn = connection.connection
    const parts: string[] = []

    if (conn.host) {
      parts.push(conn.host)
      if (conn.port) {
        parts.push(`:${conn.port}`)
      }
    } else if (conn.account) {
      parts.push(conn.account)
    } else if (conn.filepath) {
      parts.push(conn.filepath)
    }

    if (conn.database) {
      parts.push(`/${conn.database}`)
    }

    if (conn.schema) {
      parts.push(`.${conn.schema}`)
    }

    return parts.length > 0 ? parts.join('') : 'No details'
  }

  return (
    <Card hover className="h-full flex flex-col">
      <div className="p-6 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-white">
                {connection.name}
              </h3>
              {connection.is_active !== false && (
                <Badge variant="success" size="sm">
                  Active
                </Badge>
              )}
            </div>
            <Badge variant="info" size="sm" icon={<Database className="w-3 h-3" />}>
              {DATABASE_TYPE_LABELS[connection.connection.type] || connection.connection.type}
            </Badge>
          </div>
        </div>

        {/* Connection Details */}
        <div className="text-sm text-slate-400 mb-4 flex-1">
          <div className="space-y-1">
            <div className="truncate" title={getConnectionSummary()}>
              {getConnectionSummary()}
            </div>
            {connection.last_tested && (
              <div className="text-xs text-slate-500 mt-2">
                Last tested: {formatDate(connection.last_tested)}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-4 border-t border-surface-700/50">
          <Button
            variant="outline"
            size="sm"
            icon={<TestTube className="w-4 h-4" />}
            onClick={() => onTest(connection.id)}
            className="flex-1"
          >
            Test
          </Button>
          <Button
            variant="outline"
            size="sm"
            icon={<Edit className="w-4 h-4" />}
            onClick={() => onEdit(connection.id)}
            className="flex-1"
          >
            Edit
          </Button>
          {showDeleteConfirm ? (
            <div className="flex items-center gap-2 flex-1">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                loading={isDeleting}
                className="flex-1"
              >
                Confirm
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              icon={<Trash2 className="w-4 h-4" />}
              onClick={handleDelete}
              className="flex-1 text-red-600 hover:text-red-700 hover:border-red-300"
            >
              Delete
            </Button>
          )}
        </div>

        {/* Use as Source button (optional) */}
        {onUseAsSource && (
          <div className="mt-3 pt-3 border-t border-surface-700/50">
            <Button
              variant="primary"
              size="sm"
              fullWidth
              onClick={() => onUseAsSource(connection.id)}
            >
              Use as Source
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

export default ConnectionCard

