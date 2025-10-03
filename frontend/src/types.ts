export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: string[];
  recommendations?: string[];
  suggestedAnswers?: string[];  // Quick-reply suggestions
  completedSteps?: string[];
  processingTime?: number;
  tokensUsed?: number;
  metadata?: Record<string, any>;
  isError?: boolean;
}

export interface ChatRequest {
  message: string;
  user_id: string;
  session_id?: string | null;
}

export interface ChatResponse {
  response: string;
  confidence_score: number;
  sources: string[];
  recommendations: string[];
  suggested_answers?: string[];  // Quick-reply suggestions
  session_id: string;
  completed_steps: string[];
  errors: string[];
  processing_time: number;
  tokens_used: number;
  metadata: {
    workflow_type: string;
    error_count: number;
    fallback_used: boolean;
    langfuse_trace_id?: string;
  };
}

export interface FeedbackData {
  rating: number;
  comment?: string;
  session_id?: string;
  trace_id?: string;
}
