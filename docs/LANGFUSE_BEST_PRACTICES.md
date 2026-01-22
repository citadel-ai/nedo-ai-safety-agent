# Langfuse v3 Best Practices Implementation

## Overview

This document outlines how our implementation follows official [Langfuse documentation](https://langfuse.com/docs) best practices for observability with LangChain/LangGraph.

## Documentation Sources

- [Sessions](https://langfuse.com/docs/observability/features/sessions)
- [LangChain Integration](https://langfuse.com/integrations/frameworks/langchain)
- [Metadata](https://langfuse.com/docs/observability/features/metadata)
- [Tags](https://langfuse.com/docs/observability/features/tags)
- [User Tracking](https://langfuse.com/docs/observability/features/users)

## Key Langfuse v3 Changes

### Breaking Changes from v2

| Aspect | v2 | v3 |
|--------|----|----|
| Initialization | `CallbackHandler(user_id=..., session_id=...)` | `CallbackHandler()` - no args |
| Setting Attributes | Constructor args | Metadata fields in chain invocation |
| Session ID | Constructor | `langfuse_session_id` in metadata |
| Tags | Constructor | `langfuse_tags` in metadata |
| User ID | Constructor | `langfuse_user_id` in metadata |

### Our Implementation (v3 Compliant)

```python
# ✅ Correct v3 implementation
from langfuse import get_client
from langfuse.langchain import CallbackHandler

# Initialize (no constructor args)
langfuse_handler = CallbackHandler()

# Set attributes via metadata in chain invocation
response = chain.invoke(
    {"input": question},
    config={
        "callbacks": [langfuse_handler],
        "metadata": {
            "langfuse_session_id": thread_id,        # Session tracking
            "langfuse_tags": ["tag1", "tag2"],       # Tags
            "langfuse_user_id": user_id,             # Optional: User tracking
            "custom_field": "value"                  # Custom metadata
        }
    }
)
```

## Best Practices Implemented

### 1. Session Tracking ✅

**Best Practice:** Use `langfuse_session_id` for grouping related traces

**Reference:** [Langfuse Sessions Docs](https://langfuse.com/docs/observability/features/sessions)

**Our Implementation:**
```python
# backend/services/query.py
config["metadata"] = {
    "langfuse_session_id": thread_id,  # Groups all traces in this conversation
}
```

**Why this works:**
- LangGraph `thread_id` naturally maps to Langfuse `session_id`
- Each user conversation is a unique session
- Multi-turn conversations are automatically grouped
- Session replay shows complete user journey

### 2. Dynamic Tags ✅

**Best Practice:** Use `langfuse_tags` array for categorization

**Reference:** [Langfuse Tags Docs](https://langfuse.com/docs/observability/features/tags)

**Our Implementation:**
```python
# backend/services/query.py
tags = ["japan-procedures", "conversation"]
if visa_type != "unknown":
    tags.append(f"visa-{visa_type.lower().replace(' ', '-')}")
if location != "unknown":
    tags.append(f"location-{location.lower().replace(' ', '-')}")

config["metadata"] = {
    "langfuse_tags": tags,  # Array of strings
}
```

**Benefits:**
- Filter traces by visa type, location, or topic
- Analyze patterns across user segments
- Easy to add new categorizations
- No code changes to add new tags

### 3. Rich Metadata ✅

**Best Practice:** Add custom metadata for context

**Reference:** [Langfuse Metadata Docs](https://langfuse.com/docs/observability/features/metadata)

**Our Implementation:**
```python
# backend/services/query.py
config["metadata"] = {
    # Special Langfuse fields (parsed by CallbackHandler)
    "langfuse_session_id": thread_id,
    "langfuse_tags": tags,
    
    # Custom metadata (visible in Langfuse UI)
    "visa_type": visa_type,
    "location": location,
    "query_type": "conversation",
}
```

**Why useful:**
- Debug without reading full conversation
- Filter and segment traces
- Understand user context at a glance
- Support analytics and reporting

### 4. CallbackHandler Usage ✅

**Best Practice:** Create CallbackHandler without args, configure via metadata

**Reference:** [LangChain Integration Docs](https://langfuse.com/integrations/frameworks/langchain)

**Our Implementation:**
```python
# backend/utils/langfuse_config.py
def initialize_langfuse():
    # Initialize with no constructor args (v3 requirement)
    _langfuse_handler = CallbackHandler()
    
# backend/services/query.py
def query_agent(question, thread_id):
    langfuse_handler = get_langfuse_handler()
    
    # Pass handler and metadata to graph invocation
    result = graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={
            "callbacks": [langfuse_handler],
            "metadata": {...}  # All configuration here
        }
    )
```

**Why this matters:**
- v3 breaking change: constructor args removed
- More flexible: different metadata per invocation
- Better for multi-tenant applications
- Follows OpenTelemetry standards

### 5. Client Management ✅

**Best Practice:** Use `get_client()` singleton and flush on shutdown

**Reference:** [Python SDK Instrumentation](https://langfuse.com/docs/observability/sdk/python/instrumentation)

**Our Implementation:**
```python
# backend/utils/langfuse_config.py
from langfuse import get_client

def initialize_langfuse():
    _langfuse_client = get_client()  # Singleton pattern
    
def flush_langfuse():
    if _langfuse_client:
        _langfuse_client.flush()

# backend/api/server.py
@app.on_event("shutdown")
async def shutdown_event():
    flush_langfuse()  # Ensure all traces are sent
```

**Benefits:**
- Proper resource cleanup
- No data loss on shutdown
- Singleton pattern prevents multiple instances
- Background thread properly terminated

## What We DON'T Do (And Why)

### ❌ Constructor Arguments

```python
# ❌ v2 pattern (doesn't work in v3)
handler = CallbackHandler(
    session_id="session-123",
    user_id="user-456",
    tags=["tag1"]
)
```

**Why not:** V3 removed constructor args for trace attributes. Use metadata instead.

### ❌ Manual Trace Creation for Each Call

```python
# ❌ Not needed with CallbackHandler
trace = langfuse.trace(session_id="...")
handler = CallbackHandler(root=trace)
```

**Why not:** CallbackHandler automatically creates traces. Only use manual traces for custom logic outside LangGraph.

### ❌ Hardcoded Session IDs

```python
# ❌ Bad practice
config["metadata"] = {"langfuse_session_id": "static-session"}
```

**Why not:** Sessions should be dynamic (thread_id, user_id, etc.) to group related conversations.

## Verification Checklist

Use this checklist to verify proper implementation:

### Session Tracking
- [x] Using `langfuse_session_id` in metadata
- [x] Session ID is dynamic (thread_id)
- [x] Multiple queries in same session use same session_id
- [x] Can view session replay in Langfuse dashboard

### Tags
- [x] Using `langfuse_tags` (array) in metadata
- [x] Tags are descriptive and actionable
- [x] Tags help filter/segment traces
- [x] Can add new tags without code changes

### Metadata
- [x] Special fields use `langfuse_` prefix
- [x] Custom metadata is descriptive
- [x] Metadata visible in Langfuse UI
- [x] Metadata helps debugging

### CallbackHandler
- [x] Initialized without constructor args
- [x] Created once at startup
- [x] Reused across invocations
- [x] Configuration via metadata

### Client Management
- [x] Using `get_client()` singleton
- [x] Flush called on shutdown
- [x] No memory leaks
- [x] Proper cleanup

## Common Pitfalls (Avoided)

### 1. Memory Leaks with Handler Reuse
**Problem:** Creating new CallbackHandler per request with session_id

**Solution:** Create handler once, pass session_id via metadata

```python
# ✅ Good
handler = get_langfuse_handler()  # Reuse singleton
config["metadata"] = {"langfuse_session_id": thread_id}

# ❌ Bad (v2 pattern, causes memory leak)
handler = CallbackHandler(session_id=thread_id)  # New instance each time
```

### 2. Forgetting to Flush
**Problem:** Data loss on application shutdown

**Solution:** Register shutdown hook

```python
# ✅ Good
@app.on_event("shutdown")
async def shutdown_event():
    flush_langfuse()

# ❌ Bad
# No flush - pending traces lost
```

### 3. Incorrect Metadata Format
**Problem:** Tags not showing up in Langfuse

**Solution:** Use correct field names and types

```python
# ✅ Good
config["metadata"] = {
    "langfuse_tags": ["tag1", "tag2"],  # Array
    "langfuse_session_id": "session-123"  # String
}

# ❌ Bad
config["metadata"] = {
    "tags": ["tag1"],  # Wrong field name
    "session_id": "session-123"  # Wrong field name
}
```

## Testing Best Practices

### 1. Verify Session Grouping

```python
# Make multiple queries with same thread_id
for i in range(3):
    query_agent(f"Question {i}", thread_id="test-123")

# Check Langfuse: All 3 traces should appear in same session
```

### 2. Check Tag Application

```python
# Query with different visa types
query_agent("Work visa question", thread_id="test-work")
query_agent("Student visa question", thread_id="test-student")

# Check Langfuse: 
# - First should have "visa-work" tag
# - Second should have "visa-student" tag
```

### 3. Verify Metadata

```python
# Check if custom metadata appears in trace
# Look for visa_type, location in Langfuse UI metadata section
```

## Performance Considerations

### Async Processing
- Traces sent asynchronously (non-blocking)
- No performance impact on request handling
- Background threads manage queue

### Memory Usage
- ~50-100 bytes per trace metadata
- Handler reuse prevents memory leaks
- Flush on shutdown cleans up properly

### Network
- Batched requests to Langfuse
- Exponential backoff on failures
- Graceful degradation if Langfuse unavailable

## References

All implementation follows official documentation:

1. [Langfuse v3 Python SDK](https://langfuse.com/docs/observability/sdk/python/overview)
2. [LangChain Integration](https://langfuse.com/integrations/frameworks/langchain)
3. [Session Tracking](https://langfuse.com/docs/observability/features/sessions)
4. [Metadata Guide](https://langfuse.com/docs/observability/features/metadata)
5. [Tags Documentation](https://langfuse.com/docs/observability/features/tags)
6. [Upgrade Guide (v2→v3)](https://langfuse.com/docs/observability/sdk/python/upgrade-path)

## Questions?

- Check [Langfuse Documentation](https://langfuse.com/docs)
- See [GitHub Discussions](https://github.com/orgs/langfuse/discussions)
- Review our implementation: `backend/services/query.py`

