'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Activity,
  AlertTriangle,
  Database,
  BarChart3,
  MessageCircle,
  Settings,
  HardDrive,
  Table,
  Shield,
  TrendingUp,
  Bell,
  History,
  Sparkles,
  Search,
  GitBranch,
  ChevronDown,
  ChevronRight,
  FileCode,
  Layers,
  Gauge,
  Eye,
  Wrench,
  Compass,
  FolderTree,
} from 'lucide-react'
import clsx from 'clsx'

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
}

interface NavGroup {
  id: string
  name: string
  icon: React.ComponentType<{ className?: string }>
  items: NavItem[]
  defaultOpen?: boolean
}

const navigationGroups: NavGroup[] = [
  {
    id: 'monitor',
    name: 'Monitor',
    icon: Gauge,
    defaultOpen: true,
    items: [
      { name: 'Dashboard', href: '/', icon: Home },
      { name: 'Run History', href: '/runs', icon: Activity },
      { name: 'Metrics', href: '/metrics', icon: BarChart3 },
    ],
  },
  {
    id: 'quality',
    name: 'Quality',
    icon: Shield,
    defaultOpen: true,
    items: [
      { name: 'Quality Scores', href: '/quality', icon: TrendingUp },
      { name: 'Drift Analysis', href: '/drift', icon: AlertTriangle },
      { name: 'Validation Results', href: '/validation', icon: Shield },
      { name: 'Root Cause Analysis', href: '/rca', icon: Search },
      { name: 'Recommendations', href: '/recommendations', icon: Sparkles, badge: 'AI' },
    ],
  },
  {
    id: 'explore',
    name: 'Explore',
    icon: Compass,
    defaultOpen: false,
    items: [
      { name: 'Data Lineage', href: '/lineage', icon: GitBranch },
      { name: 'Table Browser', href: '/tables', icon: Table },
      { name: 'AI Chat', href: '/chat', icon: MessageCircle, badge: 'β' },
    ],
  },
  {
    id: 'configure',
    name: 'Configure',
    icon: Wrench,
    defaultOpen: false,
    items: [
      { name: 'Config Hub', href: '/config', icon: Settings },
      { name: 'Connections', href: '/config/connections', icon: Database },
      { name: 'Storage', href: '/config/storage', icon: HardDrive },
      { name: 'Quality Scoring', href: '/config/quality', icon: Gauge },
      { name: 'Data Contracts', href: '/config/contracts', icon: FolderTree },
      { name: 'Profiling', href: '/config/profiling', icon: Layers },
      { name: 'Validation Rules', href: '/config/validation', icon: Shield },
      { name: 'Drift Settings', href: '/config/drift', icon: TrendingUp },
      { name: 'Anomaly Detection', href: '/config/anomaly', icon: Eye },
      { name: 'Alert Hooks', href: '/config/hooks', icon: Bell },
      { name: 'YAML Editor', href: '/config/editor', icon: FileCode },
      { name: 'Version History', href: '/config/history', icon: History },
    ],
  },
]

function NavGroupComponent({
  group,
  isOpen,
  onToggle,
  pathname,
}: {
  group: NavGroup
  isOpen: boolean
  onToggle: () => void
  pathname: string
}) {
  const GroupIcon = group.icon
  const hasActiveItem = group.items.some(
    (item) =>
      pathname === item.href ||
      (item.href !== '/' && pathname.startsWith(item.href))
  )

  return (
    <div className="mb-1">
      {/* Group Header */}
      <button
        onClick={onToggle}
        className={clsx(
          'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200',
          hasActiveItem
            ? 'text-accent-400 bg-surface-800/50'
            : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800/30'
        )}
      >
        <div className="flex items-center gap-2.5">
          <GroupIcon className="w-4 h-4" />
          <span>{group.name}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5" />
        )}
      </button>

      {/* Group Items */}
      <div
        className={clsx(
          'overflow-hidden transition-all duration-200 ease-out',
          isOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="mt-1 ml-2 pl-3 border-l border-surface-700 space-y-0.5">
          {group.items.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href))
            const Icon = item.icon

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  'flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm transition-all duration-150',
                  isActive
                    ? 'bg-gradient-to-r from-accent-500/20 to-accent-600/10 text-accent-300 font-medium shadow-sm shadow-accent-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800/40'
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={clsx(
                      'w-4 h-4',
                      isActive ? 'text-accent-400' : 'text-slate-500'
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={clsx(
                      'px-1.5 py-0.5 text-[10px] font-bold uppercase rounded',
                      item.badge === 'AI'
                        ? 'bg-purple-500/20 text-purple-300'
                        : 'bg-amber-500/20 text-amber-300'
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function Sidebar() {
  const pathname = usePathname()

  // Initialize open states from defaultOpen values
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {}
    navigationGroups.forEach((group) => {
      initial[group.id] = group.defaultOpen ?? true
    })
    return initial
  })

  const toggleGroup = (groupId: string) => {
    setOpenGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }))
  }

  return (
    <aside className="w-64 bg-surface-900 border-r border-surface-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center shadow-lg shadow-accent-500/25">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">
              Baselinr
            </h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest">
              Quality Studio
            </p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-surface-700 to-transparent" />

      {/* Navigation Groups */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin scrollbar-thumb-surface-700 scrollbar-track-transparent">
        {navigationGroups.map((group) => (
          <NavGroupComponent
            key={group.id}
            group={group}
            isOpen={openGroups[group.id]}
            onToggle={() => toggleGroup(group.id)}
            pathname={pathname}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-surface-800">
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-600">© 2025 Baselinr</p>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-800 text-slate-500 font-mono">
            v1.0
          </span>
        </div>
      </div>
    </aside>
  )
}
