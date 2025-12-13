'use client'

import { MessageCircle } from 'lucide-react'
import ChatContainer from '@/components/chat/ChatContainer'

export default function ChatPage() {
  return (
    <div className="h-full flex flex-col p-6 lg:p-8">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-purple-500/10">
            <MessageCircle className="w-6 h-6 text-purple-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">AI Chat</h1>
          <span className="px-2 py-0.5 text-xs font-medium bg-amber-500/20 text-amber-300 rounded-full">
            Beta
          </span>
        </div>
        <p className="text-slate-400">
          Ask questions about your data quality, investigate alerts, and get insights
        </p>
      </div>
      
      <div className="flex-1 min-h-0">
        <ChatContainer />
      </div>
    </div>
  )
}
