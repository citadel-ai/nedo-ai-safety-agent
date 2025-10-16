# Langfuse v3 Integration Guide

This document explains how Langfuse v3 observability is integrated into the Japan Procedures Agent and how to use it.

## Overview

Langfuse v3 provides LLM observability and tracing for the entire LangGraph workflow, allowing you to:
- 📊 Monitor all LangGraph node executions
- 🔍 Trace LLM calls (Vertex AI Search, scope checking, fact extraction, etc.)
- 📈 Analyze performance and token usage
- 🐛 Debug conversation flows and agent decisions
- 📉 Track costs and latency across your application

## What's New in Langfuse v3

Langfuse v3 brings significant improvements:

1. **Modern API**: Uses `get_client()` for initialization and `CallbackHandler` for LangChain/LangGraph integration
2. **Simplified Tracing**: Automatic tracing via `CallbackHandler` passed to graph invocations
3. **ClickHouse Backend**: Improved scalability and performance for large-scale deployments
4. **Seamless Integration**: Works with LangChain, LangGraph, and other frameworks via callbacks

## Architecture

### Traced Components

The integration traces the following components:

#### 1. LangGraph Nodes (Spans)
- `check_query_scope` - Query scope validation
- `handle_out_of_scope` - Out-of-scope message handling
- `handle_context_drift` - Context drift detection
- `search_and_respond_with_answer` - Main Vertex AI Search execution
- `extract_facts_from_conversation` - User fact extraction
- `generate_useful_phrases` - Japanese phrase generation
- `find_useful_places` - Location search via Google Maps

#### 2. LLM Calls (Generations)
- `basic_scope_check` - Basic query scope validation
- `scope_with_context_check` - Scope check with conversation context
- All Vertex AI LLM calls within nodes (automatically traced via OTEL)

### How It Works

1. **Initialization**: `initialize_langfuse()` is called at server startup in `server.py`
   - Initializes the Langfuse client with `get_client()`
   - Creates a `CallbackHandler` for LangChain/LangGraph integration

2. **Automatic Tracing**: The `CallbackHandler` is passed to graph invocations:
   ```python
   handler = get_langfuse_handler()
   result = graph.invoke(input, config={"callbacks": [handler]})
   ```
   This automatically captures:
   - All LangGraph node executions
   - LLM calls (prompts and responses)
   - Execution time for each step
   - Errors and exceptions
   - Full conversation context

3. **Optional Decorators**: The `@observe` decorator can be used for tracing specific functions outside of LangGraph nodes

## Setup Instructions

### 1. Get Langfuse Credentials

#### Option A: Langfuse Cloud (Recommended for getting started)
1. Sign up at [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a new project
3. Go to **Settings** → **API Keys**
4. Copy your **Public Key** and **Secret Key**

#### Option B: Self-Hosted Langfuse
1. Deploy Langfuse v3 using Docker Compose (see [official docs](https://langfuse.com/docs/deployment/self-host))
2. Note your instance URL
3. Create a project and get API keys

### 2. Configure Environment Variables

Edit your `.env` file (or create one from `env_template.txt`):

```bash
# Langfuse Configuration
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...  # Your public key
LANGFUSE_SECRET_KEY=sk-lf-...  # Your secret key
LANGFUSE_HOST=https://cloud.langfuse.com  # Or your self-hosted URL
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `langfuse>=3.0.0` which is the v3 SDK with the modern API.

### 4. Run the Application

```bash
python run_server.py
```

You should see this log message on startup:
```
✅ Langfuse v3 initialized successfully. Host: https://cloud.langfuse.com
```

And when processing queries:
```
📊 Langfuse tracing enabled for thread <thread_id>
```

### 5. View Traces in Langfuse

1. Use your application (submit queries via the frontend)
2. Go to your Langfuse dashboard
3. Navigate to **Traces** to see all captured traces
4. Click on any trace to see:
   - Full execution flow (graph structure)
   - All node executions (spans)
   - LLM calls with prompts and responses
   - Token usage and costs
   - Execution times

## Usage Examples

### Viewing a Complete Conversation Flow

When a user submits a query, you'll see a trace like this:

```
📊 Trace: Query "How do I renew my work visa?"
  ├─ 🔍 check_query_scope (span)
  │   └─ 🤖 basic_scope_check (generation)
  ├─ 🔍 search_and_respond_with_answer (span)
  │   └─ 🤖 Vertex AI Search call (generation)
  ├─ 📊 extract_facts_from_conversation (span)
  │   └─ 🤖 Fact extraction LLM call (generation)
  ├─ 💬 generate_useful_phrases (span)
  │   └─ 🤖 Phrase generation LLM call (generation)
  └─ 📍 find_useful_places (span)
      └─ 🤖 Place identification LLM call (generation)
```

### Analyzing Performance

In the Langfuse dashboard, you can:
- See which nodes take the most time
- Identify bottlenecks in the LangGraph workflow
- Compare performance across different query types
- Track token usage and costs per conversation

### Debugging Issues

When errors occur:
1. Traces show exactly which node failed
2. Exception details are captured
3. Input/output data is preserved for reproduction
4. You can see the exact prompt that caused an issue

## Advanced Features

### Using the @observe Decorator

For tracing specific functions outside of LangGraph nodes:

```python
from langfuse import observe

@observe(name="custom_helper")
def my_helper_function(data):
    # Your logic here
    return result
```

The decorator will automatically trace:
- Function name and parameters
- Return values
- Execution time
- Any exceptions

### Manual Tracing with the Client

Access the Langfuse client directly for custom instrumentation:

```python
from backend.utils.langfuse_config import get_langfuse_client

client = get_langfuse_client()
if client:
    # Create custom traces, spans, or generations
    trace = client.trace(name="custom_trace")
    # ... your custom tracing logic
    client.flush()  # Ensure traces are sent
```

### Flushing Traces

Traces are automatically flushed on application shutdown, but you can manually flush if needed:

```python
from backend.utils.langfuse_config import flush_langfuse

flush_langfuse()  # Send all pending traces immediately
```

## Disabling Langfuse

To disable tracing (e.g., for testing):

```bash
# In .env file
LANGFUSE_ENABLED=false
```

Or simply don't set the `LANGFUSE_ENABLED` variable (defaults to `false`).

When disabled:
- All `@trace_node()` and `@trace_llm_call()` decorators become pass-through
- No performance impact
- No data sent to Langfuse

## Performance Considerations

Langfuse v3 is designed for production use with minimal overhead:

- **Async Processing**: Traces are sent asynchronously (non-blocking)
- **Batching**: Multiple traces are batched for efficiency
- **Local Queuing**: Traces are queued locally before sending
- **Graceful Degradation**: If Langfuse is unavailable, the app continues normally

### Resource Usage

- **Memory**: ~10-50 MB additional for trace buffering
- **Network**: Minimal (async, batched requests)
- **Latency**: <1ms per traced operation (async)

## Troubleshooting

### Traces Not Appearing

1. **Check environment variables**:
   ```bash
   echo $LANGFUSE_ENABLED
   echo $LANGFUSE_PUBLIC_KEY
   ```

2. **Check server logs**:
   - You should see: `Langfuse v3 tracing enabled`
   - If you see warnings, check your credentials

3. **Verify network access**:
   - Ensure your server can reach Langfuse host
   - Check firewall rules for outbound HTTPS

### Import Errors

If you see `ImportError: No module named 'langfuse'`:

```bash
pip install langfuse>=3.0.0
```

### Authentication Errors

If traces fail to send:
- Double-check your public and secret keys
- Ensure keys are from the correct project
- For self-hosted, verify the `LANGFUSE_HOST` URL

## Best Practices

1. **Enable in Production**: Langfuse v3 is production-ready with minimal overhead
2. **Monitor Regularly**: Review traces weekly to identify issues
3. **Set Up Alerts**: Configure alerts in Langfuse for error rates or latency spikes
4. **Tag Strategically**: Use tags to categorize traces by feature or user type
5. **Review Costs**: Track token usage to optimize LLM calls

## How the Integration Works Internally

### Architecture

1. **Initialization** (`backend/utils/langfuse_config.py`):
   - `initialize_langfuse()` creates a Langfuse client using `get_client()`
   - Creates a `CallbackHandler` instance for LangChain/LangGraph integration
   - Both are stored as module-level variables

2. **Query Processing** (`backend/services/query.py`):
   - Gets the `CallbackHandler` via `get_langfuse_handler()`
   - Passes it to `graph.invoke()` via the `config` parameter
   - All LangGraph nodes and LLM calls are automatically traced

3. **Shutdown** (`backend/api/server.py`):
   - FastAPI shutdown event calls `flush_langfuse()`
   - Ensures all pending traces are sent before the app stops

### What Gets Traced

The `CallbackHandler` automatically captures:
- **Chain/Graph Execution**: Full LangGraph workflow
- **LLM Calls**: All calls to Vertex AI (prompts, responses, tokens)
- **Tool Usage**: If you add tools to your graph
- **Errors**: Any exceptions that occur
- **Timing**: Duration of each step

No manual instrumentation needed for LangGraph nodes!

## Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse v3 Release Notes](https://langfuse.com/changelog/2025-06-05-python-sdk-v3-generally-available)
- [OpenTelemetry Overview](https://opentelemetry.io/docs/)
- [Self-Hosting Guide](https://langfuse.com/docs/deployment/self-host)

## Support

For issues or questions:
- Langfuse Community: [Discord](https://discord.gg/7NXusRtqYU)
- Documentation: [https://langfuse.com/docs](https://langfuse.com/docs)
- GitHub Issues: [https://github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)

