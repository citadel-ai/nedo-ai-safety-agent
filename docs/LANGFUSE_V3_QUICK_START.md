# Langfuse v3 Quick Start Guide

## What This Integration Does

Langfuse v3 automatically traces your entire LangGraph application, capturing:
- All node executions in the graph
- Every LLM call (prompts, responses, tokens, costs)
- Execution timing and performance metrics
- Errors and exceptions
- Full conversation context

## 5-Minute Setup

### 1. Get Langfuse Account
- Sign up at [https://cloud.langfuse.com](https://cloud.langfuse.com)
- Create a new project
- Copy your **Public Key** and **Secret Key** from Settings → API Keys

### 2. Configure Environment
Edit your `.env` file:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-1234567890abcdef
LANGFUSE_SECRET_KEY=sk-lf-abcdef1234567890
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Install & Run
```bash
# Install dependencies (includes langfuse>=3.0.0)
pip install -r requirements.txt

# Start the server
python run_server.py
```

Look for this message:
```
✅ Langfuse v3 initialized successfully. Host: https://cloud.langfuse.com
```

### 4. Test It
1. Submit a query through your application
2. Check your terminal for: `📊 Langfuse tracing enabled for thread <id>`
3. Open your Langfuse dashboard
4. Click "Traces" - you should see your query!

## What You'll See in Langfuse

Each query creates a complete trace showing:

```
📊 Japan Procedures Query
├─ check_query_scope
│  └─ ChatVertexAI (scope validation)
├─ search_and_respond_with_answer
│  └─ Vertex AI Search (grounded answer)
├─ extract_facts_from_conversation
│  └─ ChatVertexAI (fact extraction)
├─ generate_useful_phrases
│  └─ ChatVertexAI (phrase generation)
└─ find_useful_places
   └─ ChatVertexAI (place identification)
```

Click any step to see:
- Full prompt sent to the LLM
- Complete response received
- Token usage and cost
- Execution time
- Input/output data

## How It Works

The integration uses Langfuse's `CallbackHandler`:

```python
# In backend/services/query.py
handler = get_langfuse_handler()  # Get the handler
result = graph.invoke(
    {"messages": [HumanMessage(content=question)]},
    config={"callbacks": [handler]}  # Pass it to graph
)
```

That's it! The CallbackHandler automatically traces everything.

## Disabling Langfuse

To disable (e.g., for local development):

```bash
# In .env
LANGFUSE_ENABLED=false
```

Or just leave it unset - it defaults to disabled.

## Troubleshooting

### "Langfuse SDK not installed"
```bash
pip install langfuse>=3.0.0
```

### No traces appearing
1. Check environment variables: `echo $LANGFUSE_ENABLED`
2. Verify keys are correct (no extra spaces)
3. Check server logs for errors
4. Ensure your server can reach Langfuse host

### Traces delayed
Traces are sent asynchronously. Wait 10-30 seconds, then refresh your Langfuse dashboard.

## Next Steps

- **View Costs**: Check the "Costs" tab to see token usage by model
- **Set Up Alerts**: Configure alerts for errors or latency spikes
- **Filter Traces**: Use tags to filter by visa type, user, or query type
- **Export Data**: Download traces for analysis or compliance

## Resources

- Full documentation: [LANGFUSE_INTEGRATION.md](./LANGFUSE_INTEGRATION.md)
- Implementation details: [LANGFUSE_V3_IMPLEMENTATION_SUMMARY.md](./LANGFUSE_V3_IMPLEMENTATION_SUMMARY.md)
- Langfuse Docs: [https://langfuse.com/docs](https://langfuse.com/docs)

---

That's it! You now have full observability into your LangGraph application. 🎉

