/**
 * Main App Component
 * Layout: Chat on left (60%), Info Cards on right (40%)
 * Features: Loading states, removable facts, clickable places
 */

import { useState } from 'react';
import InitialForm from './components/InitialForm';
import Chat from './components/Chat';
import CollectedFacts from './components/CollectedFacts';
import UsefulPhrases from './components/UsefulPhrases';
import UsefulPlaces from './components/UsefulPlaces';
import ErrorAlert from './components/ErrorAlert';
import { setUserContext, sendMessage, removeFact } from './api';
import './index.css';

// App version - update this when deploying new versions
const APP_VERSION = '1.0.0';

function App() {
  const [threadId] = useState(() => `thread-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const [hasContext, setHasContext] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationMode, setConversationMode] = useState('multi'); // 'single' or 'multi'
  const [hasSentFirstMessage, setHasSentFirstMessage] = useState(false);
  
  // State for info cards
  const [collectedFacts, setCollectedFacts] = useState([]);
  const [usefulPhrases, setUsefulPhrases] = useState([]);
  const [usefulPlaces, setUsefulPlaces] = useState([]);
  
  // Loading states for each card (for progressive loading UX)
  const [isCardsLoading, setIsCardsLoading] = useState(false);
  
  // Error state for alert
  const [errorMessage, setErrorMessage] = useState(null);

  // Handle initial form submission
  const handleContextSubmit = async (visaType, location, mode) => {
    setConversationMode(mode);
    try {
      const result = await setUserContext(threadId, visaType, location, mode);
      
      // Display facts from LangGraph state (now a dict)
      const facts = result.collected_facts || {};
      
      // Convert dict to array format for display
      const factsArray = Object.entries(facts).map(([key, value]) => ({
        label: key,
        value: value
      }));
      
      setCollectedFacts(factsArray);
      setHasContext(true);
      setErrorMessage(null); // Clear any previous errors
    } catch (error) {
      console.error('Error setting context:', error);
      setErrorMessage('Failed to set context. Please check that the backend is running and try again.');
    }
  };

  // Handle removing a fact
  const handleRemoveFact = async (factKey) => {
    console.log('Attempting to remove fact:', factKey, 'from thread:', threadId);
    try {
      const result = await removeFact(threadId, factKey);
      console.log('Remove fact result:', result);
      
      // Update collected facts from backend response
      if (result.collected_facts) {
        const factsArray = Object.entries(result.collected_facts).map(([key, value]) => ({
          label: key,
          value: value
        }));
        setCollectedFacts(factsArray);
      }
    } catch (error) {
      console.error('Error removing fact:', error);
      setErrorMessage(`Failed to remove fact: ${error.message}`);
    }
  };

  // Handle sending a message
  const handleSendMessage = async (content) => {
    // Add user message
    const userMessage = {
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    
    // Mark that we've sent the first message (for single-turn mode)
    setHasSentFirstMessage(true);
    
    // Start cards loading (simulated progressive loading)
    setIsCardsLoading(true);

    try {
      // When switching from single to multi-turn, pass the new mode
      const modeToSend = conversationMode;
      const response = await sendMessage(content, threadId, modeToSend);

      if (response.error) {
        // Show error alert
        setErrorMessage(`Backend Error: ${response.error}`);
        // Also add to chat for context
        const errorMessage = {
          role: 'assistant',
          content: `I encountered an issue: ${response.error}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } else {
        // Clear any previous errors
        setErrorMessage(null);
        
        // Add assistant message (main answer)
        const assistantMessage = {
          role: 'assistant',
          content: response.answer,
          timestamp: new Date(),
          citations: response.citations || [],
        };
        setMessages((prev) => [...prev, assistantMessage]);
        
        // Update all cards (they arrive together, but we show loading for UX)
        // In reality, the agents run in parallel and finish together
        
        // Update collected facts from LangGraph state
        if (response.collected_facts && Object.keys(response.collected_facts).length > 0) {
          setCollectedFacts(Object.entries(response.collected_facts).map(([key, value]) => ({
            label: key,
            value: value
          })));
        }
        
        // Update useful phrases
        if (response.useful_phrases && response.useful_phrases.length > 0) {
          setUsefulPhrases(response.useful_phrases);
        }
        
        // Update useful places
        if (response.useful_places && response.useful_places.length > 0) {
          setUsefulPlaces(response.useful_places);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Show prominent error alert
      setErrorMessage('Connection Error: Unable to reach the backend server. Please make sure it is running.');
      
      // Also add to chat
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I could not connect to the server. Please check that the backend is running.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsCardsLoading(false);  // Stop cards loading
    }
  };

  // Main layout - form or chat in same position
  return (
    <div className="w-full min-h-screen lg:h-screen relative">
      {/* Error Alert */}
      <ErrorAlert message={errorMessage} onDismiss={() => setErrorMessage(null)} />
      {/* Main Layout */}
      <div className="mx-auto h-full max-w-7xl px-4 sm:px-6 py-4 sm:py-6">
        <div className="flex flex-col lg:flex-row gap-4 sm:gap-6 h-full">
          {/* Left: Form or Chat - Full width on mobile, 60% on desktop */}
          <div className="w-full lg:w-[60%] h-[70vh] sm:h-[65vh] lg:h-full flex-shrink-0">
            {!hasContext ? (
              <InitialForm onSubmit={handleContextSubmit} />
            ) : (
              <Chat
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                conversationMode={conversationMode}
                hasSentFirstMessage={hasSentFirstMessage}
                onSwitchToMultiTurn={() => {
                  setConversationMode('multi');
                  setHasSentFirstMessage(false);
                  // Next query will send 'multi' mode to backend
                }}
              />
            )}
          </div>

          {/* Right: Info Cards - Full width on mobile, 40% on desktop */}
          <div className="w-full lg:w-[40%] flex flex-col gap-4 sm:gap-6 overflow-y-auto pr-1 pb-4 lg:pb-0">
            <CollectedFacts 
              facts={collectedFacts} 
              isLoading={isCardsLoading}
              onRemoveFact={handleRemoveFact}
            />
            <UsefulPhrases 
              phrases={usefulPhrases} 
              isLoading={isCardsLoading}
            />
            <UsefulPlaces 
              places={usefulPlaces} 
              isLoading={isCardsLoading}
            />
          </div>
        </div>
      </div>
      
      {/* Version indicator */}
      <div className="fixed bottom-2 right-2 text-xs text-gray-400 select-none pointer-events-none">
        v{APP_VERSION}
      </div>
    </div>
  );
}

export default App;
