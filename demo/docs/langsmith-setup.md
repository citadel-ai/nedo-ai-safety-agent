# LangSmith Setup

LangSmith is LangChain's tracing and monitoring platform. It automatically traces all LangGraph operations via environment variables -- no code changes needed.

## Quick Setup

### 1. Get an API Key

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Settings > API Keys > create a new key (starts with `lsv2_pt_...`)

### 2. Configure

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your-key
LANGCHAIN_PROJECT=japan-procedures-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 3. Run

```bash
python run_server.py
```

Make a query, then check your project at [smith.langchain.com](https://smith.langchain.com).

## What Gets Traced

- All LangGraph node executions
- All LLM calls (ChatVertexAI, etc.)
- Tool usage and graph state changes
- Errors and exceptions
- Full conversation context

## Running Both LangSmith and Langfuse

They can run simultaneously:

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=japan-procedures-agent

LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

- **LangSmith**: automatic tracing, playground, dataset creation, run comparison
- **Langfuse**: session-based tracking, custom tags, user journey analysis

## LangSmith vs Langfuse

| Feature | LangSmith | Langfuse |
|---------|-----------|----------|
| Best for | LangGraph debugging | Production monitoring |
| Integration | Automatic via env vars | Via CallbackHandler |
| Playground | Interactive replay | Prompt management |
| Sessions | Via thread metadata | Native session tracking |

## Disabling

```bash
LANGCHAIN_TRACING_V2=false
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Traces not appearing | Verify `LANGCHAIN_TRACING_V2=true` and API key |
| Connection errors | `curl -H "x-api-key: $LANGCHAIN_API_KEY" https://api.smith.langchain.com/info` |
| Missing langsmith | `pip show langsmith` (should be >= 0.1.0) |

## Resources

- [LangSmith Documentation](https://docs.smith.langchain.com)
- [LangGraph + LangSmith](https://langchain-ai.github.io/langgraph/concepts/tracing/)
- [Evaluation Guide](https://docs.smith.langchain.com/evaluation)
