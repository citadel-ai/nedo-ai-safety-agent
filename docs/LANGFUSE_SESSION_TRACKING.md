# Langfuse Session Tracking Implementation

## Overview

Session tracking in Langfuse groups related traces together, providing a complete view of multi-turn conversations. Our implementation uses the LangGraph `thread_id` as the Langfuse `session_id` to automatically track entire user conversations.

## What is Session Tracking?

From the [Langfuse documentation](https://langfuse.com/docs/observability/features/sessions):

> Sessions in Langfuse are a way to group multiple traces together and see a simple **session replay** of the entire interaction.

In our application:
- **Session** = A complete conversation with one user (identified by `thread_id`)
- Each query/response creates a **trace** within that session
- All traces are grouped in Langfuse under the same session

## Implementation Details

### 1. Session Identification (Following Langfuse v3 Best Practices)

We use the LangGraph `thread_id` as the Langfuse `session_id` via metadata:

```python
# In backend/services/query.py
# Per Langfuse v3 docs: https://langfuse.com/docs/integrations/langchain/tracing

config["metadata"] = {
    "langfuse_session_id": thread_id,  # Special field: Maps thread_id → sessionId
    # ... other metadata
}
```

**Why this approach?**
- ✅ **Langfuse v3 Compliant**: Uses official metadata fields
- ✅ **No Constructor Args**: CallbackHandler has no args in v3 (breaking change from v2)
- ✅ **Dynamic Session Tracking**: Each invocation can have different session_id
- ✅ **Multi-turn Support**: All queries in same thread automatically grouped

This ensures:
- ✅ Each conversation thread is tracked as a unique session
- ✅ All queries in the same thread appear together in Langfuse
- ✅ Multi-turn conversations are properly grouped

### 2. Rich Metadata for Context

We enhance traces with user context metadata:

```python
config["metadata"] = {
    "langfuse_session_id": thread_id,  # Session tracking
    "visa_type": visa_type,             # User's visa type
    "location": location,               # User's location
    "query_type": "conversation",       # Type categorization
}
```

This allows you to:
- Filter sessions by visa type or location
- Understand user context without reading the conversation
- Analyze patterns across different user segments

### 3. Tags for Categorization (Langfuse Best Practice)

We automatically add tags based on user context using the special `langfuse_tags` field:

```python
# Build tags dynamically based on context
tags = ["japan-procedures", "conversation"]
if visa_type != "unknown":
    tags.append(f"visa-{visa_type.lower().replace(' ', '-')}")
if location != "unknown":
    tags.append(f"location-{location.lower().replace(' ', '-')}")

config["metadata"] = {
    "langfuse_tags": tags,  # Special field: Parsed by CallbackHandler
    # ...other metadata
}
```

**Per [Langfuse Tags Documentation](https://langfuse.com/docs/observability/features/tags):**
- `langfuse_tags` is a special metadata field
- Must be an array of strings
- Tags are applied to the trace level automatically

Example tags:
- `japan-procedures` - All traces from this app
- `conversation` - Multi-turn conversation
- `visa-work` - Work visa related queries
- `visa-student` - Student visa related queries
- `location-tokyo` - Queries from users in Tokyo
- `location-osaka` - Queries from users in Osaka

## Viewing Sessions in Langfuse

### Session List View

In your Langfuse dashboard:

1. Go to **Sessions** tab
2. You'll see all conversation threads grouped by `session_id` (thread_id)
3. Each session shows:
   - Number of traces (queries/responses)
   - Duration of the session
   - Tags and metadata
   - Last activity timestamp

### Session Detail View

Click on a session to see:

1. **Session Replay**: All traces in chronological order
2. **Timeline**: Visual representation of the conversation flow
3. **Metadata**: User context (visa type, location)
4. **Tags**: Applied tags for easy filtering
5. **Traces**: Each query-response pair as a separate trace

Example session view:
```
Session: thread-abc123
Tags: japan-procedures, conversation, visa-work, location-tokyo
Duration: 15 minutes
Traces: 5

├─ Trace 1: "How do I renew my work visa?" [2min]
│  ├─ check_query_scope
│  ├─ search_and_respond_with_answer
│  ├─ extract_facts_from_conversation
│  ├─ generate_useful_phrases
│  └─ find_useful_places
│
├─ Trace 2: "What documents do I need?" [1min]
│  └─ ...
│
└─ Trace 3: "Where is the immigration office?" [1min]
   └─ ...
```

## Use Cases

### 1. Debugging Multi-Turn Conversations

**Problem**: User reports an issue in the 3rd message of a conversation

**Solution**: 
1. Find the session using the thread_id
2. View the complete conversation replay
3. See exactly what context was collected
4. Identify where the agent went wrong

### 2. Analyzing User Journeys

**Questions you can answer**:
- How many turns do users typically need?
- What visa types generate the longest conversations?
- Which locations have users asking more questions?
- What patterns exist in successful vs. unsuccessful sessions?

**How**:
1. Filter sessions by tags (`visa-work`, `location-tokyo`, etc.)
2. Analyze session duration and trace counts
3. Look at collected facts across sessions
4. Identify common patterns

### 3. Quality Assurance

**Scenario**: Reviewing agent performance

**Process**:
1. Filter sessions by metadata (e.g., `visa_type: "work"`)
2. Review session replays to ensure accuracy
3. Add scores/annotations to sessions
4. Track improvements over time

### 4. User Segmentation

**Filter by**:
- Visa Type: `metadata.visa_type = "work"`
- Location: `metadata.location = "Tokyo"`
- Tags: `tags contains "visa-student"`

**Analyze**:
- Average session duration per segment
- Common questions per visa type
- Location-specific patterns

## Best Practices

### 1. Use Descriptive Thread IDs

✅ **Good**: `thread-user123-20250115-001`
❌ **Bad**: Random UUID with no context

Our frontend generates meaningful thread IDs that include timestamps.

### 2. Add Custom Tags

You can add custom tags based on query content:

```python
# Example: Tag queries about specific topics
if "renewal" in question.lower():
    tags.append("topic-renewal")
if "document" in question.lower():
    tags.append("topic-documents")
```

### 3. Set User IDs (Optional)

If you have user authentication, add user IDs:

```python
config["metadata"]["langfuse_user_id"] = user_id
```

This enables:
- User-level analytics
- Per-user session history
- GDPR compliance (data export/deletion by user)

### 4. Add Session Scores

After a session completes, you can add scores:

```python
from backend.utils.langfuse_config import get_langfuse_client

client = get_langfuse_client()
if client:
    client.score(
        trace_id=trace_id,
        name="user_satisfaction",
        value=5,  # 1-5 rating
        comment="User successfully found immigration office"
    )
```

## Querying Sessions

### Via Langfuse UI

**Filter examples**:
- All work visa sessions: `tags: "visa-work"`
- Tokyo users: `metadata.location: "Tokyo"`
- Long conversations: `trace_count >= 5`
- Recent sessions: `timestamp > 2024-01-01`

### Via API

```python
from backend.utils.langfuse_config import get_langfuse_client

client = get_langfuse_client()

# Get all sessions with a specific tag
sessions = client.get_sessions(
    tags=["visa-work"],
    from_timestamp="2024-01-01"
)

for session in sessions:
    print(f"Session {session.id}: {len(session.traces)} traces")
```

## Monitoring & Alerts

### Key Metrics to Track

1. **Session Duration**: Average time users spend
2. **Traces per Session**: How many questions per conversation
3. **Abandonment Rate**: Sessions with only 1 trace
4. **Success Rate**: Sessions ending with positive outcomes

### Setting Up Alerts

In Langfuse dashboard, configure alerts for:
- Sessions exceeding 10 traces (user struggling?)
- Sessions with errors
- Sessions with specific tags hitting thresholds

## Privacy Considerations

### What's Tracked

- Session IDs (thread IDs)
- User context (visa type, location)
- Full conversation content
- LLM prompts and responses

### What's NOT Tracked (by default)

- User personal information (names, emails, etc.)
- Authentication tokens
- Sensitive documents

### GDPR Compliance

To support GDPR:

1. **Add User IDs**: Map thread_id to user accounts
2. **Data Export**: Use Langfuse API to export user data
3. **Data Deletion**: Delete sessions by user_id when requested

```python
# Example: Delete all sessions for a user
client = get_langfuse_client()
sessions = client.get_sessions(user_id=user_id)
for session in sessions:
    client.delete_session(session.id)
```

## Troubleshooting

### Sessions Not Appearing

**Check**:
1. Is `LANGFUSE_ENABLED=true`?
2. Is `langfuse_session_id` in metadata?
3. Check server logs for "Langfuse tracing enabled for session"

**Debug**:
```python
# In query.py, add:
logger.info(f"Config metadata: {config.get('metadata')}")
```

### Sessions Not Grouped

**Issue**: Multiple separate sessions instead of one

**Cause**: `thread_id` changing between queries

**Solution**: Ensure frontend maintains the same thread_id for entire conversation

### Missing Metadata

**Issue**: Tags or metadata not showing

**Cause**: Metadata might not be passed correctly to CallbackHandler

**Solution**: Verify metadata format matches Langfuse expectations:
```python
config["metadata"] = {
    "langfuse_session_id": thread_id,  # Required for session grouping
    "langfuse_tags": ["tag1", "tag2"], # Optional tags
    # ... other custom metadata
}
```

## Performance Impact

Session tracking has minimal overhead:
- **Latency**: <1ms per query (async)
- **Memory**: ~50-100 bytes per session metadata
- **Network**: Bundled with existing trace data (no extra requests)

## Future Enhancements

Potential improvements:

1. **Session Summaries**: Auto-generate summaries of long sessions
2. **Session Scoring**: Automatically score sessions based on outcomes
3. **Session Recommendations**: Suggest improvements based on session patterns
4. **Real-time Monitoring**: Dashboard showing active sessions
5. **Session Analytics**: Deep dive into session patterns and trends

## References

- [Langfuse Sessions Documentation](https://langfuse.com/docs/observability/features/sessions)
- [Langfuse Metadata Guide](https://langfuse.com/docs/observability/features/metadata)
- [Langfuse Tags Documentation](https://langfuse.com/docs/observability/features/tags)
- [Langfuse User Tracking](https://langfuse.com/docs/observability/features/user-tracking)

---

## Quick Reference

### Session Tracking Checklist

- [x] Use thread_id as session_id
- [x] Add metadata (visa_type, location)
- [x] Add tags for categorization
- [x] Log session initialization
- [x] Pass metadata to CallbackHandler
- [ ] Add user_id (if authentication exists)
- [ ] Add session scoring
- [ ] Set up monitoring alerts

### Code Locations

- Session tracking setup: `backend/services/query.py`
- Session initialization: `backend/services/context.py`
- Langfuse config: `backend/utils/langfuse_config.py`
- Documentation: This file

### Useful Commands

```bash
# View session logs
grep "Langfuse tracing enabled for session" logs/app.log

# Check session metadata
grep "Context:" logs/app.log | tail -n 20

# Monitor session tags
grep "Tags:" logs/app.log | tail -n 20
```

