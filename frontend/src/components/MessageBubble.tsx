import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  UserIcon, 
  ComputerDesktopIcon,
  ClockIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import { ChatMessage } from '../types';
import { sendFeedback } from '../api';

interface MessageBubbleProps {
  message: ChatMessage;
  onQuickReply?: (reply: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onQuickReply }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const isUser = message.type === 'user';
  const isError = message.isError;

  const handleFeedback = async (rating: number) => {
    try {
      await sendFeedback({
        rating,
        session_id: message.metadata?.session_id,
        trace_id: message.metadata?.langfuse_trace_id,
      });
      setFeedbackSent(true);
    } catch (error) {
      console.error('Failed to send feedback:', error);
    }
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'} space-x-3`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser 
              ? 'bg-japan-blue text-white' 
              : isError 
                ? 'bg-red-100 text-red-600'
                : 'bg-warm-gray-100 text-warm-gray-600'
          }`}>
            {isUser ? (
              <UserIcon className="w-5 h-5" />
            ) : isError ? (
              <ExclamationTriangleIcon className="w-5 h-5" />
            ) : (
              <ComputerDesktopIcon className="w-5 h-5" />
            )}
          </div>
        </div>

        {/* Message content */}
        <div className={`flex-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {/* Message bubble */}
          <div className={`inline-block max-w-full px-4 py-3 rounded-lg ${
            isUser
              ? 'bg-japan-blue text-white'
              : isError
                ? 'bg-red-50 border border-red-200 text-red-800'
                : 'bg-white border border-warm-gray-200 text-warm-gray-800'
          }`}>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed whitespace-pre-wrap">{children}</p>,
                  h1: ({ children }) => <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-base font-semibold mb-2 mt-3 first:mt-0">{children}</h3>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1 ml-2">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1 ml-2">{children}</ol>,
                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  br: () => <br className="my-1" />,
                  hr: () => <hr className={`my-4 ${isUser ? 'border-white/30' : 'border-warm-gray-300'}`} />,
                  blockquote: ({ children }) => (
                    <blockquote className={`border-l-4 pl-4 my-3 italic ${
                      isUser ? 'border-white/50' : 'border-japan-blue text-warm-gray-700'
                    }`}>
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className={`px-1 py-0.5 rounded text-sm font-mono ${
                      isUser ? 'bg-white/20' : 'bg-warm-gray-100'
                    }`}>
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className={`p-3 rounded text-sm font-mono overflow-x-auto my-3 ${
                      isUser ? 'bg-white/20' : 'bg-warm-gray-100'
                    }`}>
                      {children}
                    </pre>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>

          {/* Metadata for assistant messages */}
          {/* Quick-reply suggestions (for assistant messages) */}
          {!isUser && message.suggestedAnswers && message.suggestedAnswers.length > 0 && onQuickReply && (
            <div className="mt-4">
              <p className="text-xs text-warm-gray-600 mb-2 font-medium">Quick replies:</p>
              <div className="flex flex-wrap gap-2">
                {message.suggestedAnswers.map((answer, idx) => (
                  <button
                    key={idx}
                    onClick={() => onQuickReply(answer)}
                    className="px-4 py-2 bg-white border-2 border-japan-blue text-japan-blue rounded-lg hover:bg-japan-blue hover:text-white transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md"
                  >
                    {answer}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!isUser && (
            <div className="mt-2 space-y-2">
              {/* Processing metadata */}
              {(message.processingTime || message.tokensUsed) && (
                <div className="flex items-center space-x-2">
                  {message.processingTime && (
                    <span className="inline-flex items-center text-xs text-warm-gray-500">
                      <ClockIcon className="w-3 h-3 mr-1" />
                      {message.processingTime.toFixed(2)}s
                    </span>
                  )}
                  {message.tokensUsed && (
                    <span className="inline-flex items-center text-xs text-warm-gray-500">
                      <CpuChipIcon className="w-3 h-3 mr-1" />
                      {message.tokensUsed} tokens
                    </span>
                  )}
                </div>
              )}

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="text-xs text-warm-gray-600">
                  <span className="font-medium">Sources:</span>{' '}
                  {message.sources.slice(0, 3).join(', ')}
                  {message.sources.length > 3 && ` +${message.sources.length - 3} more`}
                </div>
              )}

              {/* Details toggle */}
              {(message.completedSteps || message.metadata) && (
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="inline-flex items-center text-xs text-warm-gray-500 hover:text-warm-gray-700"
                >
                  <InformationCircleIcon className="w-3 h-3 mr-1" />
                  {showDetails ? 'Hide' : 'Show'} details
                </button>
              )}

              {/* Detailed information */}
              {showDetails && (
                <div className="bg-warm-gray-50 border border-warm-gray-200 rounded-lg p-3 mt-2 text-xs">
                  {message.completedSteps && (
                    <div className="mb-2">
                      <span className="font-medium">Workflow Steps:</span>{' '}
                      {message.completedSteps.join(' → ')}
                    </div>
                  )}
                  {message.metadata && (
                    <div>
                      <span className="font-medium">Metadata:</span>
                      <pre className="mt-1 text-xs overflow-x-auto">
                        {JSON.stringify(message.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Feedback buttons */}
              {!isError && !feedbackSent && (
                <div className="flex items-center space-x-2 mt-2">
                  <span className="text-xs text-warm-gray-500">Was this helpful?</span>
                  <button
                    onClick={() => handleFeedback(1)}
                    className="p-1 rounded hover:bg-green-100 text-warm-gray-400 hover:text-green-600"
                  >
                    <HandThumbUpIcon className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleFeedback(0)}
                    className="p-1 rounded hover:bg-red-100 text-warm-gray-400 hover:text-red-600"
                  >
                    <HandThumbDownIcon className="w-4 h-4" />
                  </button>
                </div>
              )}

              {feedbackSent && (
                <div className="text-xs text-green-600 mt-2">
                  Thank you for your feedback!
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs text-warm-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
