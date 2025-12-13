'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageCircle, Trash2, Sparkles, AlertCircle } from 'lucide-react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import { ChatMessage as ChatMessageType, ChatConfig, ChatResponse } from '@/types/chat'

// Generate unique IDs
const generateId = () => Math.random().toString(36).substring(2, 15)

// Example questions for empty state
const EXAMPLE_QUESTIONS = [
  "What tables have been profiled recently?",
  "Show me high severity drift events",
  "Are there any anomalies I should investigate?",
  "Compare the last two runs for customers",
  "What's the trend for null rate in the email column?",
]

export default function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<ChatConfig | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load chat config on mount
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/chat/config')
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
        if (!data.enabled) {
          setError('Chat is not configured. Please set up LLM in your config.')
        }
      } else {
        setConfig({ enabled: false, maxIterations: 5, maxHistoryMessages: 20 })
        setError('Could not load chat configuration')
      }
    } catch (err) {
      console.error('Failed to fetch chat config:', err)
      setConfig({ enabled: false, maxIterations: 5, maxHistoryMessages: 20 })
      setError('Failed to connect to chat service')
    }
  }

  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    // Add user message
    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const data: ChatResponse = await response.json()

      // Update session ID
      if (!sessionId) {
        setSessionId(data.session_id)
      }

      // Add assistant message
      const assistantMessage: ChatMessageType = {
        id: generateId(),
        role: 'assistant',
        content: data.message,
        timestamp: data.timestamp,
        toolCalls: data.tool_calls_made,
        tokensUsed: data.tokens_used,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      console.error('Chat error:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
      
      // Add error message to chat
      const errorMessage: ChatMessageType = {
        id: generateId(),
        role: 'assistant',
        content: `❌ Sorry, I encountered an error: ${err instanceof Error ? err.message : 'Unknown error'}. Please try again.`,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = async () => {
    if (sessionId) {
      try {
        await fetch(`/api/chat/session/${sessionId}`, { method: 'DELETE' })
      } catch (err) {
        console.error('Failed to clear session:', err)
      }
    }
    setMessages([])
    setSessionId(null)
    setError(null)
  }

  const handleExampleClick = (question: string) => {
    sendMessage(question)
  }

  const isConfigured = config?.enabled ?? false

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-700/50 bg-gradient-to-r from-cyan-500/10 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="font-semibold text-white">Baselinr Assistant</h2>
            <p className="text-sm text-slate-400">
              {isConfigured 
                ? `Powered by ${config?.provider || 'LLM'} (${config?.model || 'unknown'})`
                : 'Not configured'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {sessionId && (
            <span className="text-xs text-slate-500 mr-2">
              Session: {sessionId}
            </span>
          )}
          <button
            onClick={clearChat}
            disabled={messages.length === 0}
            className="
              p-2 rounded-lg text-slate-400 hover:text-slate-300 hover:bg-surface-700/50
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            "
            title="Clear conversation"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {!isConfigured && (
          <div className="flex items-start gap-3 p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-amber-400">Chat Not Configured</h3>
              <p className="text-sm text-amber-400/80 mt-1">
                To use the chat feature, configure LLM settings in your environment:
              </p>
              <pre className="mt-2 text-xs bg-surface-900/50 p-2 rounded text-slate-300 overflow-x-auto">
{`LLM_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your-api-key`}
              </pre>
            </div>
          </div>
        )}

        {messages.length === 0 && isConfigured && (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-full bg-cyan-500/20 mx-auto mb-4 flex items-center justify-center">
              <MessageCircle className="w-8 h-8 text-cyan-400" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">
              Ask me anything about your data quality
            </h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
              I can help you investigate drift events, analyze trends, compare runs, 
              and understand your data quality metrics.
            </p>

            <div className="space-y-2 max-w-lg mx-auto">
              <p className="text-sm font-medium text-slate-300 mb-3">Try asking:</p>
              {EXAMPLE_QUESTIONS.map((question, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleClick(question)}
                  className="
                    block w-full text-left px-4 py-3 rounded-lg
                    bg-surface-700/50 hover:bg-cyan-500/10 
                    text-slate-300 hover:text-cyan-300
                    border border-surface-700/50 hover:border-cyan-500/30
                    transition-colors text-sm
                  "
                >
                  &quot;{question}&quot;
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex items-center gap-3 text-slate-400">
            <div className="w-10 h-10 rounded-full bg-surface-700/50 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
            <div className="flex items-center gap-2">
              <span className="animate-pulse">Thinking</span>
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <ChatInput 
        onSend={sendMessage} 
        isLoading={isLoading}
        disabled={!isConfigured}
        placeholder={isConfigured ? "Ask about your data quality..." : "Chat not configured"}
      />
    </div>
  )
}
