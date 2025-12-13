'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import React from 'react'
import { Eye, Code, Layout, Save, AlertCircle, CheckCircle, Loader2, ChevronDown, ChevronRight, Settings, ExternalLink } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { YAMLPreview } from './YAMLPreview'
import { useConfig } from '@/hooks/useConfig'
import { toYAML, parseYAML } from '@/lib/utils/yaml'
import { isSensitiveField } from '@/lib/utils/sanitize'
import type { BaselinrConfig } from '@/types/config'

export interface ConfigEditorProps {
  onSave?: (config?: BaselinrConfig) => Promise<void>
  onValidate?: (config?: BaselinrConfig) => Promise<boolean>
}

type ViewMode = 'split' | 'visual' | 'yaml'

export function ConfigEditor({ onSave, onValidate }: ConfigEditorProps) {
  const {
    currentConfig,
    modifiedConfig,
    loadConfig,
    updateConfig,
    updateConfigPath: updateConfigPathStore,
    saveConfig,
    validateConfig,
    isLoading,
    error,
    validationErrors,
    validationWarnings,
    isDirty,
  } = useConfig()

  // Wrapper for updateConfigPath that converts string path to array
  const updateConfigPath = useCallback((path: string[], value: unknown) => {
    updateConfigPathStore(path, value)
  }, [updateConfigPathStore])

  const [viewMode, setViewMode] = useState<ViewMode>('split')
  const [yamlContent, setYamlContent] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastEdited, setLastEdited] = useState<'visual' | 'yaml'>('visual')
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Get the effective config (merged original + modifications)
  const effectiveConfig = useMemo(() => {
    return modifiedConfig && currentConfig
      ? { ...currentConfig, ...modifiedConfig }
      : currentConfig
  }, [currentConfig, modifiedConfig])

  // Convert config to YAML when visual editor changes
  useEffect(() => {
    if (effectiveConfig && lastEdited === 'visual') {
      try {
        const yaml = toYAML(effectiveConfig)
        setYamlContent(yaml)
        setIsSyncing(false)
      } catch {
        // Error handling - YAML conversion failed
        setIsSyncing(false)
      }
    }
  }, [effectiveConfig, lastEdited])

  // Load config on mount
  useEffect(() => {
    if (!currentConfig && !isLoading && loadConfig) {
      const load = async () => {
        try {
          await loadConfig()
        } catch {
          // Error handled by hook
        }
      }
      load()
    }
  }, [currentConfig, isLoading, loadConfig])

  // Initialize YAML from config
  useEffect(() => {
    if (effectiveConfig && yamlContent === '') {
      try {
        const yaml = toYAML(effectiveConfig)
        setYamlContent(yaml)
      } catch (error) {
        console.error('Failed to initialize YAML:', error)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveConfig])

  // Debounced YAML to visual sync
  const syncYAMLToVisual = useCallback(
    (yaml: string) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }

      setIsSyncing(true)
      debounceTimerRef.current = setTimeout(() => {
        try {
          const parsed = parseYAML(yaml)
          setLastEdited('yaml')
          // Update config with parsed YAML
          // updateConfig merges, so passing the full config will update all fields
          updateConfig(parsed as Partial<BaselinrConfig>)
          setIsSyncing(false)
        } catch {
          setIsSyncing(false)
        }
      }, 500)
    },
    [updateConfig]
  )

  const handleYAMLChange = (yaml: string) => {
    setYamlContent(yaml)
    setLastEdited('yaml')
    syncYAMLToVisual(yaml)
  }

  const handleVisualChange = () => {
    setLastEdited('visual')
  }

  const handleSave = async () => {
    if (!effectiveConfig) {
      setSaveStatus('error')
      return
    }

    setSaveStatus('saving')
    try {
      if (onSave) {
        await onSave(effectiveConfig)
      } else {
        await saveConfig()
      }
      setSaveStatus('success')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleValidate = async () => {
    if (!effectiveConfig) return

    try {
      if (onValidate) {
        await onValidate(effectiveConfig)
      } else {
        await validateConfig()
      }
    } catch (error) {
      console.error('Validation failed:', error)
    }
  }

  // Cleanup debounce timer
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  if (isLoading && !currentConfig) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm text-slate-400">Loading configuration...</span>
      </div>
    )
  }

  if (error && !currentConfig) {
    return (
      <div className="glass-card border-rose-500/30 bg-rose-500/10 p-4">
        <div className="flex items-center gap-2 text-rose-300">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Error loading configuration</span>
        </div>
        <p className="mt-1 text-sm text-rose-200">{error}</p>
      </div>
    )
  }

  const validationErrorsForYAML = validationErrors.map((error) => ({
    line: 0, // We don't have line numbers from validation, could enhance this
    message: error,
  }))

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="glass-card mx-6 mb-6 flex items-center justify-between p-4">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-white">Configuration Editor</h2>
          
          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-surface-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('split')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === 'split'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layout className="w-4 h-4 inline mr-1" />
              Split
            </button>
            <button
              onClick={() => setViewMode('visual')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === 'visual'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Eye className="w-4 h-4 inline mr-1" />
              Visual
            </button>
            <button
              onClick={() => setViewMode('yaml')}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === 'yaml'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Code className="w-4 h-4 inline mr-1" />
              YAML
            </button>
          </div>

          {/* Sync Indicator */}
          {isSyncing && (
            <Badge variant="info" icon={<Loader2 className="w-3 h-3 animate-spin" />}>
              Syncing...
            </Badge>
          )}

          {/* Validation Status */}
          {validationErrors.length > 0 && (
            <Badge variant="error" icon={<AlertCircle className="w-3 h-3" />}>
              {validationErrors.length} error{validationErrors.length !== 1 ? 's' : ''}
            </Badge>
          )}
          {validationWarnings.length > 0 && validationErrors.length === 0 && (
            <Badge variant="warning" icon={<AlertCircle className="w-3 h-3" />}>
              {validationWarnings.length} warning{validationWarnings.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Save Status */}
          {saveStatus === 'success' && (
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm">Saved!</span>
            </div>
          )}
          {saveStatus === 'error' && (
            <div className="flex items-center gap-2 text-rose-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Save failed</span>
            </div>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={handleValidate}
            disabled={!effectiveConfig}
          >
            Validate
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            disabled={!effectiveConfig || !isDirty || saveStatus === 'saving'}
            icon={saveStatus === 'saving' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          >
            {saveStatus === 'saving' ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Editor Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'split' && (
          <div className="grid grid-cols-2 h-full">
            {/* Visual Editor - Left */}
            <div className="border-r border-surface-700/50 overflow-y-auto bg-surface-900/30">
              <VisualConfigEditor
                config={effectiveConfig}
                onChange={handleVisualChange}
                errors={validationErrors}
                onConfigChange={(path, value) => {
                  // Update config via path
                  const pathArray = path.split('.')
                  updateConfigPath(pathArray, value)
                  handleVisualChange()
                }}
              />
            </div>

            {/* YAML Preview - Right */}
            <div className="overflow-hidden">
              <YAMLPreview
                yaml={yamlContent}
                onChange={handleYAMLChange}
                readOnly={false}
                errors={validationErrorsForYAML}
              />
            </div>
          </div>
        )}

        {viewMode === 'visual' && (
          <div className="h-full overflow-y-auto">
            <VisualConfigEditor
              config={effectiveConfig}
              onChange={handleVisualChange}
              errors={validationErrors}
              onConfigChange={(path, value) => {
                // Update config via path
                const pathArray = path.split('.')
                updateConfigPath(pathArray, value)
                handleVisualChange()
              }}
            />
          </div>
        )}

        {viewMode === 'yaml' && (
          <div className="h-full">
            <YAMLPreview
              yaml={yamlContent}
              onChange={handleYAMLChange}
              readOnly={false}
              errors={validationErrorsForYAML}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// Visual editor component - shows config in structured sections
function VisualConfigEditor({
  config,
  onChange,
  onConfigChange,
  errors = [],
}: {
  config: BaselinrConfig | null | undefined
  onChange?: () => void
  onConfigChange?: (path: string, value: unknown) => void
  errors: string[]
}) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['source', 'storage']))
  const [editingPath, setEditingPath] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<string>('')

  if (!config) {
    return (
      <div className="p-6 text-center text-slate-400">
        <p>No configuration loaded</p>
      </div>
    )
  }

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const handleStartEdit = (path: string, currentValue: unknown) => {
    setEditingPath(path)
    setEditValue(String(currentValue ?? ''))
  }

  const handleSaveEdit = (path: string, originalValue: unknown) => {
    if (!onConfigChange) return

    let newValue: unknown = editValue

    // Try to preserve type
    if (typeof originalValue === 'number') {
      newValue = parseFloat(editValue)
      if (isNaN(newValue as number)) {
        newValue = editValue // Fallback to string if not a valid number
      }
    } else if (typeof originalValue === 'boolean') {
      newValue = editValue === 'true' || editValue === '1'
    }

    onConfigChange(path, newValue)
    setEditingPath(null)
    setEditValue('')
    if (onChange) onChange()
  }

  const handleCancelEdit = () => {
    setEditingPath(null)
    setEditValue('')
  }

  const renderValue = (value: unknown, path: string = '', depth = 0): React.ReactNode => {
    const isEditing = editingPath === path
    const canEdit = depth < 3 && onConfigChange && (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
    
    // Check if this is a sensitive field and mask it for display
    const pathParts = path.split(/[\.\[\]]/).filter(Boolean)
    const fieldName = pathParts[pathParts.length - 1] || ''
    const isSensitive = isSensitiveField(fieldName)
    
    // Get display value (masked if sensitive)
    const getDisplayValue = (val: unknown): unknown => {
      if (isSensitive && typeof val === 'string' && val.length > 0 && !isEditing) {
        // Check if it's an env var reference
        if (val.startsWith('${') && val.endsWith('}')) {
          return val // Keep env var references visible
        }
        return '****' // Mask actual values
      }
      return val
    }
    
    const displayValue = getDisplayValue(value)

    if (isEditing && canEdit) {
      return (
        <div className="flex items-center gap-2">
          <Input
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSaveEdit(path, value)
              } else if (e.key === 'Escape') {
                handleCancelEdit()
              }
            }}
            onBlur={() => handleSaveEdit(path, value)}
            autoFocus
            className="flex-1 text-sm"
          />
        </div>
      )
    }

    if (value === null || value === undefined) {
      return (
        <span className="text-slate-500 italic">
          null
          {canEdit && (
            <button
              onClick={() => handleStartEdit(path, value)}
              className="ml-2 text-xs text-cyan-400 hover:text-cyan-300"
            >
              (edit)
            </button>
          )}
        </span>
      )
    }

    if (typeof value === 'string') {
      const stringDisplayValue = typeof displayValue === 'string' ? displayValue : String(displayValue)
      return (
        <span className="text-emerald-400">
          &quot;{stringDisplayValue}&quot;
          {canEdit && (
            <button
              onClick={() => handleStartEdit(path, value)}
              className="ml-2 text-xs text-cyan-400 hover:text-cyan-300"
            >
              (edit)
            </button>
          )}
        </span>
      )
    }

    if (typeof value === 'number' || typeof value === 'boolean') {
      return (
        <span className="text-cyan-400">
          {String(value)}
          {canEdit && (
            <button
              onClick={() => handleStartEdit(path, value)}
              className="ml-2 text-xs text-cyan-400 hover:text-cyan-300"
            >
              (edit)
            </button>
          )}
        </span>
      )
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-slate-500">[]</span>
      }
      return (
        <div className="ml-4">
          {value.map((item, index) => (
            <div key={index} className="ml-2">
              <span className="text-slate-400">[{index}]</span> {renderValue(item, `${path}[${index}]`, depth + 1)}
            </div>
          ))}
        </div>
      )
    }

    if (typeof value === 'object') {
      const keys = Object.keys(value)
      if (keys.length === 0) {
        return <span className="text-slate-500">{'{ }'}</span>
      }
      return (
        <div className="ml-4 space-y-1">
          {keys.map((key) => {
            const newPath = path ? `${path}.${key}` : key
            return (
              <div key={key} className="flex items-start gap-2">
                <span className="text-purple-400 font-medium">{key}:</span>
                <span className="flex-1">{renderValue((value as Record<string, unknown>)[key], newPath, depth + 1)}</span>
              </div>
            )
          })}
        </div>
      )
    }

    return <span className="text-slate-300">{String(value)}</span>
  }

  const configSections = [
    { key: 'source', label: 'Source Connection', path: '/config/connections', icon: Settings },
    { key: 'storage', label: 'Storage Configuration', path: '/config/storage', icon: Settings },
    { key: 'tables', label: 'Tables Configuration', path: '/config/tables', icon: Settings },
    { key: 'profiling', label: 'Profiling Configuration', path: '/config/profiling', icon: Settings },
    { key: 'anomaly_detection', label: 'Anomaly Detection', path: '/config/anomaly', icon: Settings },
    { key: 'validation', label: 'Validation Rules', path: '/config/validation', icon: Settings },
    { key: 'drift_detection', label: 'Drift Detection', path: '/config/drift', icon: Settings },
    { key: 'hooks', label: 'Hooks', path: '/config/hooks', icon: Settings },
  ]

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white mb-2">Visual Editor</h3>
        <p className="text-sm text-slate-400">
          View and edit configuration sections. Click &quot;(edit)&quot; on simple values to edit inline. Changes sync to YAML in real-time.
        </p>
      </div>

      {/* Configuration Sections */}
      <div className="space-y-2">
        {configSections.map((section) => {
          const sectionData = (config as unknown as Record<string, unknown>)[section.key]
          const isExpanded = expandedSections.has(section.key)
          const hasData = sectionData !== null && sectionData !== undefined

          return (
            <div
              key={section.key}
              className="glass-card border-surface-700/50 hover:border-surface-600 transition-colors"
            >
              <button
                onClick={() => toggleSection(section.key)}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-surface-800/30 rounded-t-lg"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}
                  <section.icon className="w-4 h-4 text-slate-400" />
                  <span className="font-medium text-white">{section.label}</span>
                  {hasData && (
                    <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">
                      Configured
                    </span>
                  )}
                </div>
                <a
                  href={section.path}
                  onClick={(e) => e.stopPropagation()}
                  className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                >
                  Edit <ExternalLink className="w-3 h-3" />
                </a>
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 border-t border-surface-700/50 bg-surface-800/20">
                  {hasData ? (
                    <div className="mt-3 p-3 glass-card border-surface-700/50 font-mono text-sm">
                      {renderValue(sectionData, section.key, 0)}
                    </div>
                  ) : (
                    <div className="mt-3 p-3 text-sm text-slate-500 italic">
                      No configuration set
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {/* Other/Advanced Settings */}
        {Object.keys(config).some((key) => !configSections.find((s) => s.key === key)) && (
          <div className="glass-card border-surface-700/50">
            <button
              onClick={() => toggleSection('_other')}
              className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-surface-800/30 rounded-t-lg"
            >
              <div className="flex items-center gap-2">
                {expandedSections.has('_other') ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
                <span className="font-medium text-white">Other Settings</span>
              </div>
            </button>

            {expandedSections.has('_other') && (
              <div className="px-4 pb-4 border-t border-surface-700/50 bg-surface-800/20">
                <div className="mt-3 p-3 glass-card border-surface-700/50 font-mono text-sm">
                  {Object.entries(config)
                    .filter(([key]) => !configSections.find((s) => s.key === key))
                    .map(([key, value]) => (
                      <div key={key} className="mb-2">
                        <span className="text-purple-400 font-medium">{key}:</span>{' '}
                        {renderValue(value)}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {errors.length > 0 && (
        <div className="mt-4 p-4 glass-card border-rose-500/30 bg-rose-500/10">
          <h4 className="text-sm font-medium text-rose-300 mb-2">Validation Errors:</h4>
          <ul className="list-disc list-inside space-y-1">
            {errors.map((error) => (
              <li key={error} className="text-sm text-rose-200">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 p-4 glass-card border-cyan-500/30 bg-cyan-500/10">
        <p className="text-sm text-cyan-200">
          <strong>Tip:</strong> Click on section headers to expand/collapse. Use the &quot;Edit&quot; links to
          navigate to dedicated configuration pages for detailed editing.
        </p>
      </div>
    </div>
  )
}

export default ConfigEditor

