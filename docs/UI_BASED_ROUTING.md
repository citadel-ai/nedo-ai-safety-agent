# UI-Based Single-Turn vs Multi-Turn Routing

## Overview

The system uses **user-selected conversation mode** from the UI to control routing between single-turn and multi-turn search methods. Users explicitly choose their preferred mode at the start, and can switch mid-conversation.

## How It Works

### UI Selection

```
┌─────────────────────────────────┐
│   Conversation Mode Selection   │
├─────────────────────────────────┤
│                                 │
│  [Single Turn]  [Multi Turn]   │
│                 ✓ Selected      │
│                                 │
└─────────────────────────────────┘
```

### Routing Flow

```
UI Selection → Backend State → Routing Decision

"Single Turn" → conversation_mode: "single" → search() method
"Multi Turn"  → conversation_mode: "multi"  → answer() method (with sessions)
```

## Implementation

### 1. State Definition (`backend/core/state.py`)

```python
class AgentState(MessagesState):
    # User facts
    collected_facts: Annotated[Dict[str, str], _merge_dicts] = {}
    
    # Conversation mode (set by UI)
    conversation_mode: str = "multi"  # Default to multi-turn
    
    # Vertex AI session ID (for multi-turn)
    vertex_session_id: Optional[str] = None
    
    # Response metadata
    answer: str = ""
    citations: Annotated[List[Dict], _replace_list] = []
    # ...
```

### 2. Routing Logic (`backend/core/graph.py`)

```python
def route_to_search_method(state: AgentState) -> str:
    """
    Route based on UI-selected conversation mode.
    
    Returns:
        - "search": Fast, stateless single-turn
        - "search_answer": Session-aware multi-turn
    """
    conversation_mode = state.get("conversation_mode", "multi")
    
    if conversation_mode == "single":
        logger.info("🎯 Single-turn mode → using search()")
        return "search"
    else:
        logger.info("🔄 Multi-turn mode → using answer() with sessions")
        return "search_answer"
```

### 3. Frontend Selection (`frontend/src/components/InitialForm.jsx`)

```jsx
const [conversationMode, setConversationMode] = useState('multi');

<button onClick={() => setConversationMode('single')}>
  <div>Single Turn</div>
  <div>Ask one question and get one answer</div>
</button>

<button onClick={() => setConversationMode('multi')}>
  <div>Multi Turn</div>
  <div>Have a back-and-forth conversation</div>
</button>
```

### 4. API Integration

#### Initial Context (`/api/context`)

```javascript
// Frontend
setUserContext(threadId, visaType, location, conversationMode)

// Backend
@app.post("/api/context")
async def set_context(request: UserContextRequest):
    # request.conversation_mode → stored in state
```

#### Query (`/api/query`)

```javascript
// Frontend
sendMessage(question, threadId, conversationMode)

// Backend
@app.post("/api/query")
async def query(request: QueryRequest):
    # request.conversation_mode → updates state if switching
```

## User Experience

### Single-Turn Mode

**Best for**: Quick, one-off questions

```
User: "How do I renew my residence card?"
System: [Uses search() → Fast response]

User: "What about changing my address?"
System: [Uses search() → New query, no session]
```

**Characteristics**:
- ⚡ Faster responses
- 💰 Lower cost
- 🔄 No conversation context
- 📝 Each query is independent

### Multi-Turn Mode

**Best for**: Complex questions requiring follow-ups

```
User: "How do I renew my residence card?"
System: [Uses answer() → Creates session]

User: "What documents do I need?"
System: [Uses answer() → Session-aware]
        "For the residence card renewal..."

User: "Where do I go?"
System: [Uses answer() → Understands "go" refers to renewal]
```

**Characteristics**:
- 🧠 Context-aware
- 💬 Natural follow-ups
- 📚 Session continuity
- ✨ Better for complex procedures

## Switching Modes

### "Continue as Multi-Turn" Button

After answering in single-turn mode, users can switch:

```jsx
{conversationMode === 'single' && hasSentFirstMessage && (
  <button onClick={() => setConversationMode('multi')}>
    🔄 Continue as Multi-Turn
  </button>
)}
```

When clicked:
1. Frontend updates `conversationMode` state
2. Next query sends new mode to backend
3. Backend updates state: `conversation_mode = "multi"`
4. Subsequent queries use answer() method

## Benefits

### 1. **User Control**
- Users explicitly choose their interaction style
- Clear expectations for conversation flow
- Can switch when needs change

### 2. **Predictable Behavior**
- No "magic" auto-detection
- Consistent routing based on selection
- Easy to understand and explain

### 3. **Cost Optimization**
- Users who want quick answers → single-turn (cheaper)
- Users who need conversation → multi-turn (more expensive but better)
- Transparent cost trade-off

### 4. **Flexibility**
- Can switch mid-conversation
- Mode persists in state
- Works across page reloads (via checkpointing)

## Technical Details

### State Flow

```
1. User selects mode in UI
   ↓
2. Mode sent to /api/context
   ↓
3. Stored in LangGraph state
   conversation_mode: "single" | "multi"
   ↓
4. Every query checks state
   route_to_search_method(state)
   ↓
5. Routes to appropriate method
   single → search()
   multi → answer()
```

### Mode Switching

```python
# In query service
if conversation_mode:  # New mode provided
    input_data["conversation_mode"] = conversation_mode
    logger.info(f"🔄 Switching to: {conversation_mode}")

# State automatically merges update
result = graph.invoke(input_data, config)
```

### Session Management

```python
# Multi-turn mode
if conversation_mode == "multi":
    # Use answer() method
    # Creates/maintains Vertex AI session
    # Session ID stored in state.vertex_session_id
    
# Single-turn mode
if conversation_mode == "single":
    # Use search() method
    # No session created
    # Each query is independent
```

## Comparison: Old vs New

### Before (Automatic Detection)

```python
# ❌ Automatic (confusing)
if message_count >= 2:
    return "search_answer"  # Auto-switch to multi-turn
return "search"
```

**Problems**:
- Unpredictable for users
- No way to force single-turn
- Difficult to explain behavior

### After (UI-Based)

```python
# ✅ Explicit (clear)
if conversation_mode == "single":
    return "search"
else:
    return "search_answer"
```

**Benefits**:
- User controls behavior
- Predictable and transparent
- Easy to understand

## Logging

The system logs routing decisions:

```log
🎯 Single-turn mode selected → using search() method
🔄 Multi-turn mode selected → using answer() method with sessions
🔄 Switching conversation mode to: multi
```

## API Examples

### Set Initial Context

```bash
POST /api/context
{
  "thread_id": "thread-123",
  "visa_type": "Student (留学)",
  "location": "Tokyo",
  "conversation_mode": "single"  # User's choice
}
```

### Query with Mode

```bash
POST /api/query
{
  "question": "How do I renew my visa?",
  "thread_id": "thread-123",
  "conversation_mode": null  # Use existing mode
}
```

### Switch to Multi-Turn

```bash
POST /api/query
{
  "question": "Tell me more about that",
  "thread_id": "thread-123",
  "conversation_mode": "multi"  # Switch modes
}
```

## Best Practices

### For Users

1. **Single-Turn**: Use for quick, standalone questions
   - "What is my visa renewal deadline?"
   - "Where is the immigration office?"

2. **Multi-Turn**: Use for complex procedures
   - "Guide me through changing my visa status"
   - "What do I need to do to get a residence card?"

### For Developers

1. **Always respect UI selection**
   - Don't override user's choice
   - Log mode changes clearly

2. **Default to multi-turn**
   - Better experience when unsure
   - More capabilities

3. **Make switching easy**
   - Show "Continue as Multi-Turn" button
   - Seamless mode transitions

## Summary

| Aspect | Old (Auto) | New (UI-Based) |
|--------|-----------|----------------|
| **Control** | System decides | User decides |
| **Predictability** | ❌ Unclear | ✅ Clear |
| **Flexibility** | Limited | ✅ Can switch |
| **UX** | Confusing | ✅ Transparent |
| **Cost** | Hidden | ✅ User aware |

---

**Result**: Users have full control over their conversation experience with clear, predictable behavior! 🎯

