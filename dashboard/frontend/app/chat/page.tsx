'use client'

import ChatContainer from '@/components/chat/ChatContainer'

export default function ChatPage() {
  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Data Quality Assistant</h1>
        <p className="text-gray-600 mt-1">
          Ask questions about your data quality, investigate alerts, and get insights
        </p>
      </div>
      
      <ChatContainer />
    </div>
  )
}
