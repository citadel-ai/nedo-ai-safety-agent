import { useState } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';
import MessageList from './MessageList';
import { ChatMessage } from '../types';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSendMessage,
  isLoading,
  messagesEndRef,
}) => {
  const [inputMessage, setInputMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && !isLoading) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const quickTopics = [
    { emoji: "🛂", label: "Visa & Immigration", question: "How do I renew my visa in Japan?" },
    { emoji: "🏠", label: "Housing", question: "What documents do I need for address registration?" },
    { emoji: "🏥", label: "Healthcare", question: "How do I enroll in National Health Insurance?" },
    { emoji: "🏦", label: "Banking", question: "How to open a bank account as a foreigner?" },
    { emoji: "💼", label: "Employment", question: "What are the work permit requirements?" },
    { emoji: "📋", label: "Tax", question: "What are the tax filing requirements for foreign residents?" },
  ];

  const exampleQuestions = [
    "How do I get a My Number card?",
    "What's the process for changing my visa status?",
    "How to transfer my driver's license to Japan?",
    "Where can I find English-speaking doctors?",
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          <MessageList messages={messages} onQuickReply={onSendMessage} />
          
          {/* Quick topic buttons and example questions (show only when there's just the welcome message) */}
          {messages.length === 1 && (
            <div className="mt-8 space-y-6 animate-fade-in">
              {/* Quick Topics */}
              <div>
                <h3 className="text-sm font-semibold text-warm-gray-700 mb-3 flex items-center">
                  <span className="mr-2">🚀</span>
                  Quick Topics
                </h3>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {quickTopics.map((topic, index) => (
                    <button
                      key={index}
                      onClick={() => onSendMessage(topic.question)}
                      className="flex items-center space-x-3 p-4 rounded-xl border-2 border-warm-gray-200 hover:border-japan-blue hover:shadow-md transition-all duration-200 text-left group bg-white"
                      disabled={isLoading}
                    >
                      <span className="text-2xl">{topic.emoji}</span>
                      <span className="text-sm font-medium text-warm-gray-700 group-hover:text-japan-blue">
                        {topic.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Example Questions */}
              <div>
                <h3 className="text-sm font-semibold text-warm-gray-700 mb-3 flex items-center">
                  <span className="mr-2">💭</span>
                  Popular Questions
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {exampleQuestions.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => onSendMessage(question)}
                      className="text-left p-3 rounded-lg border border-warm-gray-200 hover:border-japan-blue hover:bg-blue-50 transition-all duration-200 text-sm text-warm-gray-700 hover:text-japan-blue"
                      disabled={isLoading}
                    >
                      <span className="mr-2">→</span>
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-start space-x-3 mt-6 mb-4">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-warm-gray-100 text-warm-gray-600 flex items-center justify-center">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
              <div className="flex-1 pt-1">
                <div className="inline-block max-w-full px-4 py-3 rounded-lg bg-white border border-warm-gray-200">
                  <div className="flex items-center space-x-2">
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span className="text-sm text-warm-gray-500">Processing your request...</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-warm-gray-200 bg-white px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <div className="flex-1">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about Japanese administrative procedures..."
                className="w-full px-4 py-3 border border-warm-gray-300 rounded-lg focus:ring-2 focus:ring-japan-blue focus:border-transparent resize-none"
                rows={1}
                disabled={isLoading}
                style={{
                  minHeight: '48px',
                  maxHeight: '120px',
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="px-4 py-3 bg-japan-blue text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-japan-blue focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
            </button>
          </form>
          
          <p className="text-xs text-warm-gray-500 mt-2 text-center">
            This AI assistant provides general guidance only. Always verify information with official sources.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
