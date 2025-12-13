'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Loader2 } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  isLoading: boolean
  disabled?: boolean
  placeholder?: string
}

export default function ChatInput({ 
  onSend, 
  isLoading, 
  disabled = false,
  placeholder = "Ask about your data quality..."
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  const handleSubmit = () => {
    const trimmedInput = input.trim()
    if (trimmedInput && !isLoading && !disabled) {
      onSend(trimmedInput)
      setInput('')
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-surface-700/50 bg-surface-900/30 px-4 py-4">
      <div className="flex items-end gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading || disabled}
            rows={1}
            className="
              w-full resize-none rounded-xl border border-surface-600 
              px-4 py-3 pr-12
              bg-surface-800/50 text-white placeholder-slate-500
              focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 
              focus:outline-none
              disabled:bg-surface-900/50 disabled:text-slate-500
              transition-all
            "
            style={{ minHeight: '48px', maxHeight: '200px' }}
          />
          
          {/* Character count hint */}
          {input.length > 100 && (
            <span className="absolute right-14 bottom-3 text-xs text-slate-500">
              {input.length}/5000
            </span>
          )}
        </div>

        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading || disabled}
          className="
            flex-shrink-0 w-12 h-12 rounded-xl
            bg-cyan-500 text-white
            flex items-center justify-center
            hover:bg-cyan-600
            disabled:bg-surface-700 disabled:text-slate-500 disabled:cursor-not-allowed
            transition-colors
          "
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Help text */}
      <p className="mt-2 text-xs text-slate-500 text-center">
        Press <kbd className="px-1.5 py-0.5 bg-surface-800 rounded text-slate-300">Enter</kbd> to send, 
        <kbd className="px-1.5 py-0.5 bg-surface-800 rounded text-slate-300 ml-1">Shift+Enter</kbd> for new line
      </p>
    </div>
  )
}
