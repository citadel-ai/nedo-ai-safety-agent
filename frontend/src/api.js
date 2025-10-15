/**
 * API Module
 * Handles all communication with the backend
 */

/**
 * Set user context (visa type, location, and conversation mode) for a thread
 */
export async function setUserContext(threadId, visaType, location, conversationMode = 'multi') {
  const response = await fetch('/api/context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: threadId,
      visa_type: visaType,
      location: location,
      conversation_mode: conversationMode,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to set user context');
  }

  return response.json();
}

/**
 * Send a message to the agent
 */
export async function sendMessage(question, threadId, conversationMode = null) {
  const body = {
    question,
    thread_id: threadId,
  };
  
  // Only include conversation_mode if provided (for mid-conversation switching)
  if (conversationMode) {
    body.conversation_mode = conversationMode;
  }
  
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get thread state (for debugging or display)
 */
export async function getThreadState(threadId) {
  const response = await fetch(`/api/thread/${threadId}`);
  
  if (!response.ok) {
    throw new Error('Failed to get thread state');
  }
  
  return response.json();
}

/**
 * Remove a fact from collected_facts
 */
export async function removeFact(threadId, factKey) {
  console.log('API: Removing fact', factKey, 'from thread', threadId);
  const response = await fetch(`/api/thread/${threadId}/facts`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fact_key: factKey,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    console.error('Remove fact failed:', response.status, errorData);
    throw new Error(errorData.detail || `Failed to remove fact (${response.status})`);
  }

  return response.json();
}

/**
 * Check backend health
 */
export async function checkHealth() {
  const response = await fetch('/api/health');
  if (!response.ok) {
    throw new Error('Backend is offline');
  }
  return response.json();
}

