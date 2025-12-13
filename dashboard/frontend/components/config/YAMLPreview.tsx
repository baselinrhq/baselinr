'use client'

import { useState, useRef, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { Copy, Check, AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { formatYAML, validateYAML } from '@/lib/utils/yaml'

  // Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-sm text-slate-400">Loading editor...</div>
    </div>
  ),
})

export interface YAMLPreviewProps {
  yaml: string
  onChange?: (yaml: string) => void
  readOnly?: boolean
  errors?: Array<{ line: number; message: string }>
  onValidate?: (yaml: string) => void
  className?: string
}

export function YAMLPreview({
  yaml,
  onChange,
  readOnly = false,
  errors = [],
  onValidate,
  className = '',
}: YAMLPreviewProps) {
  const [copied, setCopied] = useState(false)
  const [editorValue, setEditorValue] = useState(yaml)
  const [validationError, setValidationError] = useState<string | null>(null)
  const editorRef = useRef<{ getValue: () => string } | null>(null)

  // Sync external yaml prop to editor
  useEffect(() => {
    if (yaml !== editorValue) {
      setEditorValue(yaml)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yaml])

  const handleEditorChange = (value: string | undefined) => {
    const newValue = value || ''
    setEditorValue(newValue)
    
    // Validate YAML syntax
    const validation = validateYAML(newValue)
    if (!validation.valid) {
      setValidationError(validation.error || 'Invalid YAML')
    } else {
      setValidationError(null)
    }
    
    // Call onChange if provided
    if (onChange) {
      onChange(newValue)
    }
    
    // Call onValidate if provided
    if (onValidate && validation.valid) {
      onValidate(newValue)
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(editorValue)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }

  const handleFormat = () => {
    try {
      const formatted = formatYAML(editorValue)
      setEditorValue(formatted)
      if (onChange) {
        onChange(formatted)
      }
    } catch (error) {
      console.error('Failed to format YAML:', error)
    }
  }

  const handleEditorDidMount = (
    editor: { getValue: () => string },
    monaco: { languages: { setLanguageConfiguration: (lang: string, config: unknown) => void } }
  ) => {
    editorRef.current = editor
    
    // Configure Monaco for YAML
    monaco.languages.setLanguageConfiguration('yaml', {
      comments: {
        lineComment: '#',
      },
      brackets: [
        ['{', '}'],
        ['[', ']'],
      ],
      autoClosingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '"', close: '"' },
        { open: "'", close: "'" },
      ],
    })
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-surface-700/50 bg-surface-900/50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">YAML Preview</span>
          {validationError && (
            <Badge variant="error" icon={<AlertCircle className="w-3 h-3" />}>
              Syntax Error
            </Badge>
          )}
          {errors.length > 0 && (
            <Badge variant="warning" icon={<AlertCircle className="w-3 h-3" />}>
              {errors.length} validation error{errors.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!readOnly && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleFormat}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Format
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopy}
            icon={copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 relative">
        <MonacoEditor
          height="100%"
          language="yaml"
          value={editorValue}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            automaticLayout: true,
            tabSize: 2,
            insertSpaces: true,
            formatOnPaste: true,
            formatOnType: true,
            renderValidationDecorations: 'on',
            scrollbar: {
              vertical: 'auto',
              horizontal: 'auto',
            },
          }}
        />
      </div>

      {/* Error Messages */}
      {(validationError || errors.length > 0) && (
        <div className="px-4 py-2 border-t border-surface-700/50 glass-card border-rose-500/30 bg-rose-500/10 max-h-32 overflow-y-auto">
          {validationError && (
            <div className="flex items-start gap-2 text-sm text-rose-200">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{validationError}</span>
            </div>
          )}
          {errors.map((error, index) => (
            <div key={index} className="flex items-start gap-2 text-sm text-rose-200 mt-1">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>
                Line {error.line}: {error.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default YAMLPreview

