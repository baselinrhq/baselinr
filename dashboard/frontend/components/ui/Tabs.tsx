'use client'

import { useState, useCallback, useRef } from 'react'
import { cn, generateId } from '@/lib/utils'

export interface Tab {
  id: string
  label: string
  icon?: React.ReactNode
  disabled?: boolean
}

export interface TabsProps {
  tabs: Tab[]
  activeTab?: string
  defaultActiveTab?: string
  defaultTab?: string
  onChange?: (tabId: string) => void
  orientation?: 'horizontal' | 'vertical'
  className?: string
  children?: (activeTab: string) => React.ReactNode
}

export function Tabs({
  tabs,
  activeTab: controlledActiveTab,
  defaultActiveTab,
  defaultTab,
  onChange,
  orientation = 'horizontal',
  className,
  children,
}: TabsProps) {
  const id = useRef(generateId('tabs')).current
  
  // Support controlled and uncontrolled modes
  const isControlled = controlledActiveTab !== undefined
  const [internalActiveTab, setInternalActiveTab] = useState(
    defaultActiveTab || defaultTab || tabs[0]?.id || ''
  )
  const activeTab = isControlled ? controlledActiveTab : internalActiveTab
  
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map())

  // Handle tab selection
  const handleTabClick = useCallback(
    (tab: Tab) => {
      if (tab.disabled) return
      
      if (!isControlled) {
        setInternalActiveTab(tab.id)
      }
      
      onChange?.(tab.id)
    },
    [isControlled, onChange]
  )

  // Get enabled tabs for keyboard navigation
  const enabledTabs = tabs.filter(tab => !tab.disabled)

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, tabIndex: number) => {
      const currentEnabledIndex = enabledTabs.findIndex(
        t => t.id === tabs[tabIndex].id
      )
      
      let nextIndex: number

      switch (event.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          event.preventDefault()
          nextIndex =
            currentEnabledIndex < enabledTabs.length - 1
              ? currentEnabledIndex + 1
              : 0
          break
        case 'ArrowLeft':
        case 'ArrowUp':
          event.preventDefault()
          nextIndex =
            currentEnabledIndex > 0
              ? currentEnabledIndex - 1
              : enabledTabs.length - 1
          break
        case 'Home':
          event.preventDefault()
          nextIndex = 0
          break
        case 'End':
          event.preventDefault()
          nextIndex = enabledTabs.length - 1
          break
        default:
          return
      }

      const nextTab = enabledTabs[nextIndex]
      if (nextTab) {
        tabRefs.current.get(nextTab.id)?.focus()
        handleTabClick(nextTab)
      }
    },
    [enabledTabs, tabs, handleTabClick]
  )

  const isHorizontal = orientation === 'horizontal'

  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'w-full',
          !isHorizontal && 'flex gap-4',
        )}
      >
        {/* Tab list */}
        <div
          role="tablist"
          aria-orientation={orientation}
          className={cn(
            'inline-flex p-1 rounded-lg bg-surface-800/50',
            isHorizontal
              ? 'flex-row gap-1'
              : 'flex-col gap-1'
          )}
        >
          {tabs.map((tab, index) => {
            const isActive = tab.id === activeTab
            const isDisabled = tab.disabled

            return (
              <button
                key={tab.id}
                ref={el => {
                  if (el) tabRefs.current.set(tab.id, el)
                }}
                role="tab"
                id={`${id}-tab-${tab.id}`}
                aria-controls={`${id}-panel-${tab.id}`}
                aria-selected={isActive}
                aria-disabled={isDisabled}
                tabIndex={isActive ? 0 : -1}
                onClick={() => handleTabClick(tab)}
                onKeyDown={e => handleKeyDown(e, index)}
                disabled={isDisabled}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md',
                  'transition-all duration-150 focus:outline-none',
                  'focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900',
                  isActive
                    ? 'bg-surface-700 text-white shadow-sm'
                    : isDisabled
                    ? 'text-slate-600 cursor-not-allowed'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-700/50'
                )}
              >
                {tab.icon && (
                  <span className="flex-shrink-0 w-4 h-4">{tab.icon}</span>
                )}
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>
      
      {/* Tab content */}
      {children && (
        <div className="mt-4">
          {children(activeTab)}
        </div>
      )}
    </div>
  )
}

// TabPanel component for content
export interface TabPanelProps {
  children: React.ReactNode
  tabId: string
  activeTab: string
  className?: string
}

export function TabPanel({
  children,
  tabId,
  activeTab,
  className,
}: TabPanelProps) {
  const isActive = tabId === activeTab
  
  if (!isActive) return null

  return (
    <div
      role="tabpanel"
      id={`tabs-panel-${tabId}`}
      aria-labelledby={`tabs-tab-${tabId}`}
      tabIndex={0}
      className={cn('focus:outline-none', className)}
    >
      {children}
    </div>
  )
}

// Combined Tabs component with children support
export interface TabsWithContentProps extends Omit<TabsProps, 'children'> {
  children?: React.ReactNode
}

export function TabsWithContent({
  children,
  ...tabsProps
}: TabsWithContentProps) {
  const [activeTab, setActiveTab] = useState(
    tabsProps.activeTab ||
      tabsProps.defaultActiveTab ||
      tabsProps.tabs[0]?.id ||
      ''
  )

  const currentActiveTab = tabsProps.activeTab ?? activeTab

  const handleChange = (tabId: string) => {
    if (tabsProps.activeTab === undefined) {
      setActiveTab(tabId)
    }
    tabsProps.onChange?.(tabId)
  }

  return (
    <div className="w-full">
      <Tabs {...tabsProps} activeTab={currentActiveTab} onChange={handleChange} />
      <div className="pt-4">
        {children}
      </div>
    </div>
  )
}

export default Tabs
