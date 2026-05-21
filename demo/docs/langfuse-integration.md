# Langfuse v3 Integration

Langfuse v3 provides LLM observability for the entire LangGraph workflow: node executions, LLM calls, token usage, costs, latency, and errors.

## Setup

### 1. Get Credentials

Sign up at [cloud.langfuse.com](https://cloud.langfuse.com), create a project, and copy your Public Key and Secret Key from Settings > API Keys.

For self-hosted: deploy Langfuse v3 via Docker Compose (see [official docs](https://langfuse.com/docs/deployment/self-host)).

### 2. Configure

```bash
# .env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Run

```bash
python run_server.py
# Look for: "Langfuse v3 initialized successfully"
```

Submit a query and check the Langfuse dashboard under Traces.

## How It Works

The integration uses Langfuse's `CallbackHandler` passed to graph invocations:

```python
handler = get_langfuse_handler()
result = graph.invoke(
    {"messages": [HumanMessage(content=question)]},
    config={
        "callbacks": [handler],
        "metadata": {
            "langfuse_session_id": thread_id,
            "langfuse_tags": ["japan-procedures", "visa-work"],
            "visa_type": visa_type,
            "location": location,
        }
    }
)
```

This automatically captures all LangGraph node executions, LLM calls (prompts, responses, tokens), execution timing, and errors. No manual instrumentation needed for LangGraph nodes.

### Traced Components

| Component | Type | Description |
|-----------|------|-------------|
| `check_query_scope` | Span | Query scope validation |
| `search_and_respond_with_answer` | Span | Vertex AI Search execution |
| `extract_facts_from_conversation` | Span | User fact extraction |
| `generate_useful_phrases` | Span | Japanese phrase generation |
| `find_useful_places` | Span | Google Maps location search |

### Session Tracking

The LangGraph `thread_id` maps to Langfuse `session_id` via the `langfuse_session_id` metadata field. All queries in the same thread are grouped in the same session.

### Tags

Tags are added dynamically based on context:

```python
tags = ["japan-procedures", "conversation"]
if visa_type != "unknown":
    tags.append(f"visa-{visa_type.lower().replace(' ', '-')}")
```

### Architecture

1. **Initialization** (`backend/utils/langfuse_config.py`): `initialize_langfuse()` creates a singleton `CallbackHandler`
2. **Query Processing** (`backend/services/query.py`): handler is passed to `graph.invoke()` via config
3. **Shutdown** (`backend/api/server.py`): `flush_langfuse()` ensures pending traces are sent

## Using `@observe` for Custom Functions

```python
from langfuse import observe

@observe(name="custom_helper")
def my_helper_function(data):
    return result
```

## Disabling

Set `LANGFUSE_ENABLED=false` (or leave it unset). All tracing becomes a no-op with zero performance impact.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Traces not appearing | Verify env vars: `LANGFUSE_ENABLED`, keys, host |
| Import errors | `pip install langfuse>=3.0.0` |
| Auth errors | Double-check keys match the correct project |
| Traces delayed | Traces are sent async; wait 10-30s and refresh |

## Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Integration](https://langfuse.com/integrations/frameworks/langchain)
- [Session Tracking](https://langfuse.com/docs/observability/features/sessions)
