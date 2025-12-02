/**
 * Chat types for the Baselinr Dashboard
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: number;
  tokensUsed?: number;
}

export interface ChatSession {
  sessionId: string;
  messages: ChatMessage[];
  isLoading: boolean;
  error?: string;
}

export interface ChatConfig {
  enabled: boolean;
  provider?: string;
  model?: string;
  maxIterations: number;
  maxHistoryMessages: number;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  role: string;
  timestamp: string;
  tool_calls_made: number;
  tokens_used?: number;
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
}

export interface SessionStats {
  session_id: string;
  duration_seconds: number;
  total_messages: number;
  total_tokens_used: number;
  total_tool_calls: number;
}
