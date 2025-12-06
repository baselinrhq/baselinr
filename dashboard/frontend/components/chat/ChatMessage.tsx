'use client'

import { Bot, User, Wrench, Clock } from 'lucide-react'
import { ChatMessage as ChatMessageType } from '@/types/chat'
import ReactMarkdown from 'react-markdown'

interface ChatMessageProps {
  message: ChatMessageType
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } catch {
      return ''
    }
  }

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`
        flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
        ${isUser ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-600'}
      `}>
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      {/* Message Content */}
      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`
          rounded-2xl px-4 py-3
          ${isUser 
            ? 'bg-primary-600 text-white rounded-br-md' 
            : 'bg-gray-100 text-gray-900 rounded-bl-md'}
        `}>
          {isAssistant ? (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown
                components={{
                  // Style code blocks
                  code: ({ className, children, ...props }) => {
                    const isInline = !className
                    return isInline ? (
                      <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props}>
                        {children}
                      </code>
                    ) : (
                      <code className={`${className} block bg-gray-800 text-gray-100 p-3 rounded-lg my-2 overflow-x-auto`} {...props}>
                        {children}
                      </code>
                    )
                  },
                  // Style tables
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="min-w-full border-collapse border border-gray-300">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-gray-300 px-3 py-2 bg-gray-50 text-left font-medium">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-gray-300 px-3 py-2">
                      {children}
                    </td>
                  ),
                  // Style lists
                  ul: ({ children }) => (
                    <ul className="list-disc pl-5 my-2 space-y-1">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-5 my-2 space-y-1">
                      {children}
                    </ol>
                  ),
                  // Style headings
                  h1: ({ children }) => (
                    <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold mt-3 mb-2">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-bold mt-2 mb-1">{children}</h3>
                  ),
                  // Style strong/bold
                  strong: ({ children }) => (
                    <strong className="font-semibold">{children}</strong>
                  ),
                  // Style links
                  a: ({ children, href }) => (
                    <a href={href} className="text-primary-600 hover:underline" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Metadata */}
        <div className={`
          flex items-center gap-3 mt-1 text-xs text-gray-500
          ${isUser ? 'flex-row-reverse' : ''}
        `}>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatTime(message.timestamp)}
          </span>
          
          {message.toolCalls && message.toolCalls > 0 && (
            <span className="flex items-center gap-1">
              <Wrench className="w-3 h-3" />
              {message.toolCalls} tool{message.toolCalls > 1 ? 's' : ''}
            </span>
          )}
          
          {message.tokensUsed && (
            <span className="text-gray-400">
              {message.tokensUsed.toLocaleString()} tokens
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
