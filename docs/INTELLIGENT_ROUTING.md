# ⚠️ OUTDATED - See UI_BASED_ROUTING.md Instead

> **Note**: This document describes the old automatic routing approach. The system now uses **user-selected conversation mode** from the UI instead of automatic detection.
> 
> **For current implementation, see**: `UI_BASED_ROUTING.md`

---

# Intelligent Single-Turn vs Multi-Turn Routing (OLD APPROACH)

## Overview

~~The system now **automatically** chooses between single-turn and multi-turn search methods based on conversation state, eliminating the need for manual configuration.~~

**UPDATED**: The system now uses UI-based selection where users explicitly choose "Single Turn" or "Multi Turn" mode.

## How It Works

### Automatic Method Selection

```
First Query:     search()  → Fast, stateless, single-turn
Follow-Up Query: answer()  → Session-aware, multi-turn with context
```

### Decision Logic

The routing is handled in `backend/core/graph.py`:

```python
def route_to_search_method(state: AgentState) -> str:
    # 1. Check for existing session
    if vertex_session_id exists:
        return "search_answer"  # Continue multi-turn
    
    # 2. Check message count
    if message_count >= 2:
        return "search_answer"  # Follow-up query
    
    # 3. Default to single-turn
    return "search"  # First query
```

## Benefits

### Single-Turn Search (search method)
- ✅ **Faster**: No session overhead
- ✅ **Lower cost**: Fewer API calls
- ✅ **Simpler**: Stateless processing
- ✅ **Perfect for**: One-off questions

### Multi-Turn Answer (answer method)
- ✅ **Context-aware**: Remembers conversation history
- ✅ **Better follow-ups**: Understands references ("it", "that", "there")
- ✅ **Query rephrasing**: Automatically improves follow-up queries
- ✅ **Session continuity**: Maintains context across queries

## Example Flow

### Scenario 1: Single Question

```
User: "How do I get a residence card?"
→ search() method used
→ Fast response, no session created
```

### Scenario 2: Conversation

```
User: "How do I get a residence card?"
→ search() method used (first query)
→ Response provided

User: "What documents do I need?"
→ answer() method used (follow-up detected)
→ Session created automatically
→ Context-aware response

User: "Where do I go?"
→ answer() method used (existing session)
→ Continues with same session
→ Understands "go" refers to residence card application
```

## Technical Details

### State Management

The system tracks conversation state via:

1. **`vertex_session_id`**: Stored in LangGraph state
   - `None`: No session (use search)
   - `"abc123..."`: Active session (use answer)

2. **Message count**: From `state["messages"]`
   - `< 2 messages`: First query
   - `≥ 2 messages`: Follow-up query

### Session Creation

Sessions are created automatically by the Vertex AI Answer API:

```python
# In vertex_answer.py
request = discoveryengine_v1.AnswerQueryRequest(
    session=session_name,  # "-" for auto-creation
    query=query,
    # ... other config
)

response = client.answer_query(request)
# Response includes session.name for future use
```

The session ID is extracted and stored:

```python
# Extract session ID from response
session_name = response.session.name  
# "projects/.../sessions/abc123"

# Store in state for next query
state["vertex_session_id"] = "abc123"
```

### Query Enhancement

Both methods enhance queries with collected facts:

```python
collected_facts = {
    "Visa Type": "Student Visa",
    "Location": "Tokyo"
}

# Original query
"What documents do I need?"

# Enhanced query
"What documents do I need? (Context: Visa Type: Student Visa, Location: Tokyo)"
```

## Migration from USE_ANSWER_METHOD

### Before (Manual Configuration)

```env
# .env file
USE_ANSWER_METHOD=false  # Or true
```

```python
# In graph.py
if Config.USE_ANSWER_METHOD:
    return "search_answer"
return "search"
```

### After (Automatic Detection)

```python
# In graph.py - NO env variable needed
if vertex_session_id:
    return "search_answer"  # Has session

if message_count >= 2:
    return "search_answer"  # Follow-up

return "search"  # First query
```

### Removed Files/Config

- ❌ `Config.USE_ANSWER_METHOD` (removed from config.py)
- ❌ `USE_ANSWER_METHOD` (removed from env_template.txt)
- ❌ `--set-env-vars "USE_ANSWER_METHOD=..."` (removed from deploy script)

## Benefits of This Approach

1. **User Experience**: Seamless transition from single to multi-turn
2. **Performance**: Fast single-turn for one-off questions
3. **Cost Efficiency**: Only use multi-turn when beneficial
4. **No Configuration**: Works automatically, no setup needed
5. **Natural Conversation**: Users can ask follow-ups without thinking

## Logging

The system logs its routing decisions:

```
🆕 First query (1 messages) → using search() method
💬 Follow-up query detected (3 messages) → using answer() method with multi-turn
🔄 Existing session → using answer() method
```

## Future Enhancements

Potential improvements:

1. **Explicit Multi-Turn Toggle**: UI button to force multi-turn mode
2. **Session Timeout**: Auto-reset sessions after inactivity
3. **Hybrid Mode**: Use search for facts, answer for follow-ups
4. **Smart Detection**: ML-based follow-up detection
5. **Cost Tracking**: Monitor single vs multi-turn usage

## API Comparison

### Search Method (search)

```python
# Uses search API
from langchain_google_community.vertex_ai_search import VertexAISearchSummaryTool

tool = VertexAISearchSummaryTool(
    project_id=project,
    data_store_id=datastore,
    # No session support
)

response = tool.invoke(query)
# Returns summary with citations
```

### Answer Method (answer)

```python
# Uses conversational search API
from google.cloud import discoveryengine_v1

client = ConversationalSearchServiceClient()

request = AnswerQueryRequest(
    serving_config=config,
    query=query,
    session=session,  # ✅ Session support!
    # ... query understanding, answer generation specs
)

response = client.answer_query(request)
# Returns answer with session ID and citations
```

## Testing

To test the routing:

```python
# Test 1: First query (should use search)
response1 = graph.invoke(
    {"messages": [("user", "How do I apply?")]},
    config={"configurable": {"thread_id": "test-1"}}
)
# Check logs: "🆕 First query → using search() method"

# Test 2: Follow-up (should use answer)
response2 = graph.invoke(
    {"messages": [("user", "What about fees?")]},
    config={"configurable": {"thread_id": "test-1"}}
)
# Check logs: "💬 Follow-up query detected → using answer() method"
```

## Conclusion

The intelligent routing system provides the best of both worlds:
- **Fast** single-turn for standalone questions
- **Context-aware** multi-turn for conversations
- **Automatic** - no configuration needed
- **Cost-effective** - only use multi-turn when beneficial

No more `USE_ANSWER_METHOD` environment variable! 🎉

