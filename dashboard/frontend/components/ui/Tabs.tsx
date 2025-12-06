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
  onChange?: (tabId: string) => void
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

export function Tabs({
  tabs,
  activeTab: controlledActiveTab,
  defaultActiveTab,
  onChange,
  orientation = 'horizontal',
  className,
}: TabsProps) {
  const id = useRef(generateId('tabs')).current
  
  // Support controlled and uncontrolled modes
  const isControlled = controlledActiveTab !== undefined
  const [internalActiveTab, setInternalActiveTab] = useState(
    defaultActiveTab || tabs[0]?.id || ''
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
    <div
      className={cn(
        'w-full',
        !isHorizontal && 'flex gap-4',
        className
      )}
    >
      {/* Tab list */}
      <div
        role="tablist"
        aria-orientation={orientation}
        className={cn(
          isHorizontal
            ? 'flex border-b border-gray-200'
            : 'flex flex-col border-r border-gray-200 pr-4'
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
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium',
                'transition-colors focus:outline-none',
                'focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset',
                isHorizontal
                  ? '-mb-px border-b-2'
                  : '-mr-px border-r-2',
                isActive
                  ? 'border-primary-600 text-primary-600'
                  : isDisabled
                  ? 'border-transparent text-gray-400 cursor-not-allowed'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
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
export interface TabsWithContentProps extends TabsProps {
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
