# LangGraph Time Travel Support

## ✅ Yes, Time Travel is Fully Supported

Our current setup **fully supports** LangGraph time travel functionality thanks to the checkpointing implementation.

## What is Time Travel?

Time travel in LangGraph allows you to:
1. **Rewind** execution to any previous checkpoint
2. **Modify** the state at that checkpoint
3. **Resume** execution from the modified state
4. **Explore** different execution paths

**Reference:** [LangGraph Time Travel Docs](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/)

## Current Implementation

### 1. Checkpointing ✅

**File:** `backend/core/graph.py`

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
```

**Why it works:**
- Every graph execution creates checkpoints
- Checkpoints are stored with `thread_id` and `checkpoint_id`
- State is persisted at each node execution

### 2. State History Access ✅

**File:** `backend/services/query.py`

```python
def get_thread_history(thread_id: str) -> List[dict]:
    """Get full checkpoint history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    history = []
    
    for state in graph.get_state_history(config):
        history.append({
            "checkpoint_id": state.config["configurable"]["checkpoint_id"],
            "timestamp": state.metadata.get("ts"),
            "message_count": len(state.values.get("messages", [])),
            "collected_facts_count": len(state.values.get("collected_facts", {})),
            "has_error": bool(state.values.get("error"))
        })
    
    return history
```

**Why it works:**
- `get_state_history()` retrieves all checkpoints for a thread
- Checkpoints are in reverse chronological order
- Each checkpoint has state, config, and metadata

### 3. State Modification ✅

**File:** `backend/services/query.py`

```python
def remove_collected_fact(thread_id: str, fact_key: str) -> dict:
    """Remove a specific fact from collected_facts."""
    config = {"configurable": {"thread_id": thread_id}}
    
    snapshot = graph.get_state(config)
    collected_facts = snapshot.values.get("collected_facts", {})
    
    # Remove the fact
    updated_facts = {k: v for k, v in collected_facts.items() if k != fact_key}
    
    # Update state at current checkpoint
    graph.update_state(
        config,
        {"collected_facts": updated_facts},
        as_node="__start__"
    )
```

**Why it works:**
- `update_state()` modifies state at a checkpoint
- Creates a new checkpoint with modified state
- Can be used to "rewrite history"

## How to Use Time Travel

### Example 1: Rewind to a Previous State

```python
from backend.core.graph import graph

# 1. Get the thread history
config = {"configurable": {"thread_id": "thread-123"}}
history = list(graph.get_state_history(config))

# 2. Select a previous checkpoint (e.g., 2nd to last)
previous_checkpoint = history[1]
checkpoint_id = previous_checkpoint.config["configurable"]["checkpoint_id"]

# 3. Resume from that checkpoint
new_config = {
    "configurable": {
        "thread_id": "thread-123",
        "checkpoint_id": checkpoint_id
    }
}

# 4. Continue execution from that point
result = graph.invoke(
    {"messages": [HumanMessage(content="New question")]},
    new_config
)
```

### Example 2: Modify State and Resume

```python
# 1. Get current state
config = {"configurable": {"thread_id": "thread-123"}}
snapshot = graph.get_state(config)

# 2. Modify the state
new_config = graph.update_state(
    config,
    values={
        "collected_facts": {
            "Visa Type": "student",  # Changed from "work"
            "Location": "Osaka"      # Changed from "Tokyo"
        }
    },
    as_node="__start__"
)

# 3. Resume execution from modified state
result = graph.invoke(None, new_config)
```

### Example 3: Create Alternate Timeline

```python
# 1. Get to a specific checkpoint
config = {"configurable": {"thread_id": "thread-123"}}
history = list(graph.get_state_history(config))
checkpoint = history[2]  # Go back 2 steps

# 2. Modify state at that checkpoint
new_config = graph.update_state(
    checkpoint.config,
    values={"answer": "Alternative answer here"},
    as_node="search_answer"
)

# 3. Create new timeline from that point
result = graph.invoke(None, new_config)
# This creates a new branch in the execution history
```

## Use Cases for Time Travel

### 1. Debugging

**Scenario:** User reports wrong answer in 3rd message

**Solution:**
```python
# Rewind to before the wrong answer
history = list(graph.get_state_history(config))
before_error = history[5]  # Checkpoint before the error

# Inspect state
print(before_error.values)
print(before_error.next)  # See which node executed next

# Modify and retry
new_config = graph.update_state(
    before_error.config,
    values={"some_param": "corrected_value"}
)
result = graph.invoke(None, new_config)
```

### 2. User Corrections

**Scenario:** User wants to correct a fact mid-conversation

**Solution:**
```python
# Current implementation already supports this!
remove_collected_fact(thread_id, "Visa Type")

# Then continue conversation - agent will use corrected facts
```

### 3. A/B Testing

**Scenario:** Test different responses for same user input

**Solution:**
```python
# Get checkpoint before answer generation
config = {"configurable": {"thread_id": "thread-123"}}
history = list(graph.get_state_history(config))
before_answer = history[1]

# Version A: Original
result_a = graph.invoke(None, before_answer.config)

# Version B: Modified parameters
new_config = graph.update_state(
    before_answer.config,
    values={"temperature": 0.9}  # More creative
)
result_b = graph.invoke(None, new_config)

# Compare results
```

### 4. What-If Analysis

**Scenario:** Explore different user contexts

**Solution:**
```python
# Start from beginning
config = {"configurable": {"thread_id": "thread-123"}}
history = list(graph.get_state_history(config))
initial_state = history[-1]  # First checkpoint

# Scenario 1: Work visa in Tokyo
config_1 = graph.update_state(
    initial_state.config,
    values={"collected_facts": {"Visa Type": "work", "Location": "Tokyo"}}
)
result_1 = graph.invoke({"messages": [HumanMessage("Need help")]}, config_1)

# Scenario 2: Student visa in Kyoto
config_2 = graph.update_state(
    initial_state.config,
    values={"collected_facts": {"Visa Type": "student", "Location": "Kyoto"}}
)
result_2 = graph.invoke({"messages": [HumanMessage("Need help")]}, config_2)
```

## API Endpoint Ideas

### Potential New Endpoints

```python
# backend/api/server.py

@app.get("/api/thread/{thread_id}/history")
async def get_checkpoint_history(thread_id: str):
    """Get all checkpoints for a thread (already exists!)"""
    return get_thread_history(thread_id)

@app.post("/api/thread/{thread_id}/rewind")
async def rewind_to_checkpoint(thread_id: str, checkpoint_id: str):
    """Rewind to a specific checkpoint"""
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }
    snapshot = graph.get_state(config)
    return {
        "checkpoint_id": checkpoint_id,
        "state": snapshot.values,
        "next": snapshot.next
    }

@app.post("/api/thread/{thread_id}/fork")
async def fork_from_checkpoint(
    thread_id: str,
    checkpoint_id: str,
    new_thread_id: str,
    state_updates: dict = None
):
    """Create a new thread from a checkpoint"""
    # Get the checkpoint
    old_config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }
    
    # Create new thread with same state
    new_config = {"configurable": {"thread_id": new_thread_id}}
    snapshot = graph.get_state(old_config)
    
    graph.update_state(
        new_config,
        values=state_updates or snapshot.values,
        as_node="__start__"
    )
    
    return {"new_thread_id": new_thread_id}
```

## Limitations

### Current Limitations

1. **In-Memory Storage**: Using `MemorySaver` means checkpoints are lost on restart
   - **Solution:** Use PostgresSaver for persistence
   
2. **No Checkpoint Visualization**: No UI for browsing checkpoints
   - **Solution:** Build a checkpoint browser in frontend

3. **No Automatic Branching**: Forks must be manual
   - **Solution:** Add automatic fork creation for modifications

### Memory Checkpointer vs PostgreSQL Checkpointer

| Feature | MemorySaver (Current) | PostgresSaver |
|---------|----------------------|---------------|
| **Persistence** | Lost on restart | Persisted to database |
| **Performance** | Fast (in-memory) | Slightly slower (DB) |
| **Scalability** | Single instance | Multi-instance |
| **Production** | ❌ Not recommended | ✅ Recommended |

**To upgrade to PostgreSQL:**

```python
# backend/core/graph.py
from langgraph.checkpoint.postgres import PostgresSaver

# Replace MemorySaver with PostgresSaver
DB_URI = "postgresql://user:pass@localhost/dbname"
checkpointer = PostgresSaver.from_conn_string(DB_URI)
graph = workflow.compile(checkpointer=checkpointer)
```

## Compatibility with Langfuse

**Question:** Does time travel work with Langfuse tracing?

**Answer:** ✅ Yes! They work together seamlessly:

- **Langfuse traces execution**: Each invocation creates a trace
- **LangGraph stores checkpoints**: State is persisted
- **Time travel creates new traces**: Rewinding and resuming creates new traces
- **Session tracking preserved**: Same `thread_id` keeps all traces in same session

### Example: Time Travel + Langfuse

```python
# 1. Original execution (creates trace 1)
result = query_agent("Question 1", thread_id="thread-123")
# Langfuse: Trace 1 in session "thread-123"

# 2. Another query (creates trace 2)
result = query_agent("Question 2", thread_id="thread-123")
# Langfuse: Trace 2 in session "thread-123"

# 3. Rewind to checkpoint (creates trace 3)
history = list(graph.get_state_history(config))
old_config = history[1].config
result = graph.invoke(None, old_config)
# Langfuse: Trace 3 in session "thread-123" (with same session_id!)

# All 3 traces appear in same Langfuse session
```

## Summary

✅ **Time Travel Fully Supported**
- Checkpointing enabled via MemorySaver
- State history accessible via `get_state_history()`
- State modification via `update_state()`
- Resume execution via `invoke(None, config)`

✅ **Works with Langfuse**
- Time travel operations are traced
- Session tracking preserved
- Complete observability of rewinds and modifications

✅ **Production Considerations**
- Switch to PostgresSaver for persistence
- Add UI for checkpoint browsing
- Implement automatic fork management
- Set up checkpoint retention policies

**Reference:**
- [LangGraph Time Travel Docs](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/)
- [Checkpointing Concepts](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [PostgresSaver Reference](https://langchain-ai.github.io/langgraph/reference/checkpoints/#postgressaver)

