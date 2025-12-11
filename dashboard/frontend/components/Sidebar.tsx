'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Activity, AlertTriangle, Database, BarChart3, MessageCircle, Settings, HardDrive, Table, Shield, TrendingUp, Bell } from 'lucide-react'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Runs', href: '/runs', icon: Activity },
  { name: 'Drift Detection', href: '/drift', icon: AlertTriangle },
  { name: 'Validation Dashboard', href: '/validation', icon: Shield },
  { name: 'Lineage', href: '/lineage', icon: Database },
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
  { name: 'Chat', href: '/chat', icon: MessageCircle },
  { name: 'Configuration', href: '/config', icon: Settings },
  { name: 'Config Editor', href: '/config/editor', icon: Settings },
  { name: 'Connections', href: '/config/connections', icon: Settings },
  { name: 'Storage', href: '/config/storage', icon: HardDrive },
  { name: 'Tables', href: '/config/tables', icon: Table },
  { name: 'Profiling', href: '/config/profiling', icon: BarChart3 },
  { name: 'Anomaly Detection', href: '/config/anomaly', icon: TrendingUp },
  { name: 'Validation', href: '/config/validation', icon: Shield },
  { name: 'Drift Detection', href: '/config/drift', icon: TrendingUp },
  { name: 'Hooks', href: '/config/hooks', icon: Bell },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-white border-r border-gray-200">
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="px-6 py-8">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">Baselinr</h1>
              <p className="text-xs text-gray-500">Dashboard v2.0</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-50'
                )}
              >
                <Icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            © 2024 Baselinr
          </p>
        </div>
      </div>
    </div>
  )
}

