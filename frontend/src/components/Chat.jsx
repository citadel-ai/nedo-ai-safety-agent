/**
 * Chat Component
 * Main chat interface with message list and input field
 */

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

// Collapsible Sources Component
function CollapsibleSources({ citations }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-200">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium">
          {citations.length} {citations.length === 1 ? 'Source' : 'Sources'}
        </span>
      </button>

      {isOpen && (
        <div className="mt-3 space-y-3 pl-5">
          {citations.map((citation, idx) => {
            // Handle both old format (string) and new format (object)
            if (typeof citation === 'string') {
              return (
                <div key={idx} className="text-xs text-gray-600">
                  [{idx + 1}] {citation}
                </div>
              );
            }
            
            // New format with URL, title, pages
            return (
              <div key={idx} className="text-xs">
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-blue-700 flex-shrink-0">
                    [{citation.citation_number || idx + 1}]
                  </span>
                  <div className="flex-1">
                    {citation.url ? (
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
                      >
                        {citation.title || `Document ${citation.citation_number || idx + 1}`}
                      </a>
                    ) : (
                      <span className="font-medium text-gray-700">
                        {citation.title || `Document ${citation.citation_number || idx + 1}`}
                      </span>
                    )}
                    {citation.source_type && (
                      <span className="text-gray-500 ml-2">({citation.source_type})</span>
                    )}
                    {citation.pages && citation.pages.length > 0 && (
                      <div className="text-gray-600 mt-1">
                        📄 Pages: {citation.pages.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Chat({ messages, onSendMessage, isLoading, conversationMode = 'multi', hasSentFirstMessage = false, onSwitchToMultiTurn }) {
  const [input, setInput] = useState('');
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);
  const messagesContainerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const prevMessagesLength = useRef(messages.length);
  const prevIsLoading = useRef(isLoading);
  
  // Check if input should be disabled (single-turn mode after first message)
  const isInputDisabled = isLoading || (conversationMode === 'single' && hasSentFirstMessage);

  // Check if there's more content below
  const checkScrollIndicator = () => {
    if (!messagesContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
    const scrolledToBottom = scrollHeight - scrollTop - clientHeight < 50;
    
    setShowScrollIndicator(!scrolledToBottom && messages.length > 0);
  };

  // Smart scrolling when loading starts (user sends message)
  useEffect(() => {
    // When loading starts, scroll to bottom to show loading dots
    if (isLoading && !prevIsLoading.current) {
      scrollToBottom();
    }
    prevIsLoading.current = isLoading;
  }, [isLoading]);

  // Smart scrolling when new messages arrive
  useEffect(() => {
    if (messages.length > prevMessagesLength.current) {
      const lastMessage = messages[messages.length - 1];
      
      // If it's a new assistant message (response just arrived)
      if (lastMessage && lastMessage.role === 'assistant' && !isLoading) {
        // Check if the message is long
        const messageLength = lastMessage.content.length;
        
        if (messageLength > 500) {
          // For long messages, scroll to show user's question and start of response
          // Instead of scrolling to the very bottom
          smartScrollToNewResponse();
        } else {
          // For short messages, scroll to bottom normally
          scrollToBottom();
        }
      }
    }
    
    prevMessagesLength.current = messages.length;
    checkScrollIndicator();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  const smartScrollToNewResponse = () => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const { scrollHeight, clientHeight } = container;
    
    // Scroll to show about 70% down (shows user message + beginning of response)
    const targetScroll = scrollHeight - clientHeight * 1.5;
    
    container.scrollTo({
      top: Math.max(0, targetScroll),
      behavior: 'smooth'
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isInputDisabled) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isInputDisabled) {
        onSendMessage(input.trim());
        setInput('');
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-1 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gray-900 text-white flex items-center justify-center shadow-md">JP</div>
          <div>
            <h1 className="text-lg font-semibold leading-tight text-gray-900">Japan Helpdesk</h1>
            <p className="text-sm text-gray-500">Visas, housing, and everyday life</p>
          </div>
        </div>
      </div>

      {/* Messages - relative container for scroll indicator */}
      <div className="flex-1 relative">
        <div 
          ref={messagesContainerRef}
          onScroll={checkScrollIndicator}
          className="absolute inset-0 overflow-y-auto p-2 sm:p-4 md:p-6 space-y-4"
        >
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-6xl mb-4">👋</div>
                <h2 className="text-xl font-semibold mb-2 text-gray-800">Welcome!</h2>
                <p className="text-gray-600 mb-6">Ask me anything about living in Japan.</p>
                <div className="text-left max-w-md mx-auto space-y-2">
                  <p className="text-sm font-semibold text-gray-700">Try asking:</p>
                  <p className="text-sm text-gray-600">• "How do I renew my work visa in Tokyo?"</p>
                  <p className="text-sm text-gray-600">• "I need to change my visa status to permanent resident"</p>
                  <p className="text-sm text-gray-600">• "Where can I get help with housing in Osaka?"</p>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'user' ? (
                <div className="max-w-[60%] rounded-2xl px-4 py-3 text-white shadow-md bg-gradient-to-br from-zinc-700/95 to-zinc-600/95">
                  <div className="whitespace-pre-wrap break-words">{message.content}</div>
                </div>
              ) : (
                <div className="max-w-[75%] px-1 py-0.5 text-gray-800">
                  <div className="markdown-content">
                    <ReactMarkdown
                      components={{
                        p: ({node, ...props}) => <p className="mb-2 last:mb-0 leading-relaxed" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-2 space-y-1" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-2 space-y-1" {...props} />,
                        li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
                        strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                        em: ({node, ...props}) => <em className="italic" {...props} />,
                        code: ({node, inline, ...props}) =>
                          inline
                            ? <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props} />
                            : <code className="block bg-gray-200 p-2 rounded my-2 text-sm overflow-x-auto" {...props} />,
                        h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-2 mt-3" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-lg font-bold mb-2 mt-2" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-base font-bold mb-1 mt-2" {...props} />,
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                  {message.citations && <CollapsibleSources citations={message.citations} />}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-gray-200 px-4 py-2 bg-white shadow">
                <div className="flex items-center gap-1">
                  <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
                  <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
                  <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Scroll Indicator - White gradient + arrow */}
        {showScrollIndicator && (
          <div className="absolute bottom-0 left-0 right-0 h-24 pointer-events-none">
            {/* White gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-white via-white/80 to-transparent"></div>
            
            {/* Arrow button */}
            <button
              onClick={scrollToBottom}
              className="absolute bottom-2 left-1/2 transform -translate-x-1/2 pointer-events-auto bg-gray-800 hover:bg-gray-900 text-white rounded-full p-2 shadow-lg transition-all"
              title="Scroll to bottom"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-2 sm:p-3">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              conversationMode === 'single' && hasSentFirstMessage
                ? "Single-turn conversation ended"
                : "Type your question... Include any relevant details."
            }
            disabled={isInputDisabled}
            rows={3}
            className="w-full resize-none min-h-[80px] max-h-48 px-4 py-3 pr-10 border border-gray-200 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
        {conversationMode === 'single' && hasSentFirstMessage ? (
          <div className="mt-2 text-xs text-gray-600 flex items-center gap-2">
            <span>💡 Single-turn mode:</span>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="text-blue-600 hover:text-blue-800 underline"
            >
              Refresh page
            </button>
            <span>or</span>
            <button
              type="button"
              onClick={onSwitchToMultiTurn}
              className="text-blue-600 hover:text-blue-800 underline"
            >
              Switch to Multi-turn
            </button>
          </div>
        ) : (
          <div className="mt-1 text-xs text-gray-500">Press Enter to send, Shift+Enter for newline</div>
        )}
      </form>
    </div>
  );
}

