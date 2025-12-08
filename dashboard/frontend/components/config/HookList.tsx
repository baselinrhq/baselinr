'use client'

import { HookWithId } from '@/types/hook'
import { HookCard } from './HookCard'

export interface HookListProps {
  hooks: HookWithId[]
  hooksEnabled: boolean
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTest?: (id: string) => void
}

export function HookList({
  hooks,
  hooksEnabled: _hooksEnabled, // eslint-disable-line @typescript-eslint/no-unused-vars
  onEdit,
  onDelete,
  onTest,
}: HookListProps) {
  if (hooks.length === 0) {
    return null
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {hooks.map((hook) => (
        <HookCard
          key={hook.id}
          hook={hook}
          onEdit={onEdit}
          onDelete={onDelete}
          onTest={onTest}
        />
      ))}
    </div>
  )
}

export default HookList

