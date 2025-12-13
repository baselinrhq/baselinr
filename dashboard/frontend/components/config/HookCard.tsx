'use client'

import { useState } from 'react'
import { Edit, Trash2, Bell, Database, MessageSquare, Code, FileText } from 'lucide-react'
import { HookWithId } from '@/types/hook'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

export interface HookCardProps {
  hook: HookWithId
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTest?: (id: string) => void
}

const HOOK_TYPE_LABELS: Record<string, string> = {
  logging: 'Logging',
  sql: 'SQL',
  snowflake: 'Snowflake',
  slack: 'Slack',
  custom: 'Custom',
}

const HOOK_TYPE_ICONS: Record<string, React.ReactNode> = {
  logging: <FileText className="w-4 h-4" />,
  sql: <Database className="w-4 h-4" />,
  snowflake: <Database className="w-4 h-4" />,
  slack: <MessageSquare className="w-4 h-4" />,
  custom: <Code className="w-4 h-4" />,
}

export function HookCard({
  hook,
  onEdit,
  onDelete,
  onTest,
}: HookCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const handleDelete = () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true)
      return
    }
    onDelete(hook.id)
  }

  const getHookSummary = () => {
    const h = hook.hook
    const parts: string[] = []

    if (h.type === 'slack') {
      if (h.channel) {
        parts.push(`Channel: ${h.channel}`)
      }
      if (h.min_severity) {
        parts.push(`Min severity: ${h.min_severity}`)
      }
    } else if (h.type === 'sql' || h.type === 'snowflake') {
      if (h.table_name) {
        parts.push(`Table: ${h.table_name}`)
      }
    } else if (h.type === 'logging') {
      if (h.log_level) {
        parts.push(`Level: ${h.log_level}`)
      }
    } else if (h.type === 'custom') {
      if (h.class_name) {
        parts.push(`Class: ${h.class_name}`)
      }
    }

    return parts.length > 0 ? parts.join(' • ') : 'No details'
  }

  const isEnabled = hook.hook.enabled !== false

  return (
    <Card hover className="h-full flex flex-col">
      <div className="p-6 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge
                variant="info"
                size="sm"
                icon={HOOK_TYPE_ICONS[hook.hook.type] || <Bell className="w-3 h-3" />}
              >
                {HOOK_TYPE_LABELS[hook.hook.type] || hook.hook.type}
              </Badge>
              {isEnabled ? (
                <Badge variant="success" size="sm">
                  Enabled
                </Badge>
              ) : (
                <Badge variant="warning" size="sm">
                  Disabled
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Hook Details */}
        <div className="text-sm text-slate-400 mb-4 flex-1">
          <div className="space-y-1">
            <div className="truncate" title={getHookSummary()}>
              {getHookSummary()}
            </div>
            {hook.last_tested && (
              <div className="text-xs text-slate-500 mt-2">
                Last tested: {new Date(hook.last_tested).toLocaleString()}
              </div>
            )}
            {hook.test_status && (
              <div className="text-xs mt-1">
                <Badge
                  variant={hook.test_status === 'success' ? 'success' : 'error'}
                  size="sm"
                >
                  {hook.test_status}
                </Badge>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-4 border-t border-surface-700/50">
          {onTest && (
            <Button
              variant="outline"
              size="sm"
              icon={<Edit className="w-4 h-4" />}
              onClick={() => onTest(hook.id)}
              className="flex-1"
            >
              Test
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            icon={<Edit className="w-4 h-4" />}
            onClick={() => onEdit(hook.id)}
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
              className="flex-1 text-rose-400 hover:text-rose-300 hover:border-rose-500/50"
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

export default HookCard

