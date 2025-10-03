import { useState, useRef, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import { ChatMessage, ChatResponse } from './types';
import { sendMessage } from './api';

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: `# 🇯🇵 Welcome to Japan Helpdesk!

こんにちは！日本での生活をサポートします。

I'm your AI assistant for navigating life in Japan. I provide guidance on administrative procedures, regulations, and everyday matters that foreigners commonly encounter.

## 🎯 How I Can Help

**Immigration & Visas**
Get information about visa applications, renewals, and status changes.

**Housing & Registration**
Learn about finding housing, registering your address, and utilities setup.

**Healthcare & Insurance**
Understand the healthcare system, insurance enrollment, and medical services.

**Finance & Tax**
Navigate banking, tax filing, pension, and financial matters.

**Employment & Education**
Find information about work permits, job regulations, and educational opportunities.

---

💡 **Tip**: Use the example questions below or ask me anything about living in Japan!`,
      timestamp: new Date(),
      sources: [],
      recommendations: []
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId] = useState(`user_${Date.now()}`);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendMessage({
        message: content,
        user_id: userId,
        session_id: sessionId,
      });

      // Update session ID if this is the first message
      if (!sessionId) {
        setSessionId(response.session_id);
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date(),
        confidence: response.confidence_score,
        sources: response.sources,
        recommendations: response.recommendations,
        suggestedAnswers: response.suggested_answers,  // Quick-reply suggestions
        completedSteps: response.completed_steps,
        processingTime: response.processing_time,
        tokensUsed: response.tokens_used,
        metadata: response.metadata,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.',
        timestamp: new Date(),
        confidence: 0,
        sources: ['error'],
        recommendations: ['Try rephrasing your question', 'Contact support if the issue continues'],
        isError: true,
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([messages[0]]); // Keep the welcome message
    setSessionId(null);
  };

  return (
    <div className="flex h-screen bg-warm-gray-50">
      {/* Sidebar */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)}
        onClearChat={clearChat}
        sessionId={sessionId}
        messageCount={messages.length - 1} // Exclude welcome message
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <Header 
          onMenuClick={() => setSidebarOpen(true)}
          sessionId={sessionId}
        />
        
        <main className="flex-1 overflow-hidden">
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            messagesEndRef={messagesEndRef}
          />
        </main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
export default App;

