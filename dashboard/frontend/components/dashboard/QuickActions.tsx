'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/Button'
import { Play, AlertTriangle, Settings, Sparkles } from 'lucide-react'

export default function QuickActions() {
  return (
    <div className="glass-card p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link href="/runs">
          <Button
            variant="primary"
            size="md"
            fullWidth
            icon={<Play className="w-4 h-4" />}
            className="justify-start"
          >
            Start New Run
          </Button>
        </Link>
        
        <Link href="/drift">
          <Button
            variant="outline"
            size="md"
            fullWidth
            icon={<AlertTriangle className="w-4 h-4" />}
            className="justify-start"
          >
            View All Alerts
          </Button>
        </Link>
        
        <Link href="/config/validation">
          <Button
            variant="outline"
            size="md"
            fullWidth
            icon={<Settings className="w-4 h-4" />}
            className="justify-start"
          >
            Configure Validation
          </Button>
        </Link>
        
        <Link href="/recommendations">
          <Button
            variant="outline"
            size="md"
            fullWidth
            icon={<Sparkles className="w-4 h-4" />}
            className="justify-start"
          >
            View Recommendations
          </Button>
        </Link>
      </div>
    </div>
  )
}
