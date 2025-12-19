'use client'

import { isDemoMode } from '@/lib/demo-mode'
import { AlertCircle, ExternalLink } from 'lucide-react'

export default function DemoModeBanner() {
  if (!isDemoMode()) {
    return null
  }

  return (
    <div className="bg-warning-500/10 border-b border-warning-500/20 px-4 py-2">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-warning-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-warning-100 font-medium">
              Demo Mode
            </p>
            <p className="text-xs text-warning-200/80 mt-0.5">
              This is a read-only demonstration. All data is pre-generated.
            </p>
          </div>
        </div>
        <a
          href="https://baselinr.io/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-warning-200 hover:text-warning-100 transition-colors whitespace-nowrap"
        >
          View Documentation
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  )
}
