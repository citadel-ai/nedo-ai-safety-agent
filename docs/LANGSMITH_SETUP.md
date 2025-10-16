# LangSmith Integration Guide

## Overview

LangSmith is LangChain's official tracing and monitoring platform, designed specifically for LangChain and LangGraph applications. It provides powerful debugging, testing, and monitoring capabilities.

## LangSmith vs Langfuse

Both can run simultaneously! Here's how they compare:

| Feature | LangSmith | Langfuse |
|---------|-----------|----------|
| **Best For** | LangChain/LangGraph debugging | General LLM observability |
| **Integration** | Native LangChain support | Via CallbackHandler |
| **Setup** | Environment variables only | SDK initialization required |
| **Traces** | Automatic for all LangChain | Via callbacks |
| **Time Travel** | ✅ Built-in replay | ✅ Via checkpoints |
| **Datasets** | ✅ Built-in | ✅ Via API |
| **Evaluations** | ✅ Built-in | ✅ Built-in |
| **Playground** | ✅ Interactive | ✅ Prompt management |

**Recommendation:** Use **both**!
- **LangSmith** for development/debugging (automatic tracing)
- **Langfuse** for production monitoring (session tracking, tags)

## Quick Setup (5 minutes)

### 1. Get LangSmith API Key

1. Go to [https://smith.langchain.com](https://smith.langchain.com)
2. Sign up or log in (free tier available)
3. Click your profile → **Settings** → **API Keys**
4. Create a new API key
5. Copy the key (starts with `lsv2_pt_...`)

### 2. Configure Environment Variables

Edit your `.env` file:

```bash
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your-api-key-here
LANGCHAIN_PROJECT=japan-procedures-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

**That's it!** No code changes needed.

### 3. Run Your Application

```bash
python run_server.py
```

### 4. View Traces

1. Make a query through your application
2. Go to [https://smith.langchain.com](https://smith.langchain.com)
3. Navigate to your project: **japan-procedures-agent**
4. See all traces automatically!

## How It Works

LangSmith automatically traces all LangChain/LangGraph operations via environment variables:

```python
# No code changes needed!
# LangGraph automatically sends traces when these env vars are set:
# - LANGCHAIN_TRACING_V2=true
# - LANGCHAIN_API_KEY=your-key
```

**What gets traced:**
- ✅ All LangGraph node executions
- ✅ All LLM calls (ChatVertexAI, etc.)
- ✅ Tool usage
- ✅ Graph state changes
- ✅ Errors and exceptions
- ✅ Full conversation context

## Running Both LangSmith and Langfuse

**Yes, you can run both simultaneously!**

```bash
# .env file
# LangSmith (automatic tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=japan-procedures-agent

# Langfuse (session tracking + tags)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

**What happens:**
- **LangSmith**: Captures all LangChain operations automatically
- **Langfuse**: Captures via CallbackHandler with session tracking

**Benefits:**
- LangSmith: Better for debugging individual runs
- Langfuse: Better for session analysis and user journeys

## Testing Locally

### Test 1: Basic Tracing

```bash
# Enable LangSmith
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_pt_your-key
export LANGCHAIN_PROJECT=japan-procedures-test

# Run server
python run_server.py

# Make a query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I renew my work visa?", "thread_id": "test-123"}'

# Check LangSmith dashboard
# You should see a new trace appear immediately
```

### Test 2: Session Tracking

```python
# test_langsmith.py
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_..."
os.environ["LANGCHAIN_PROJECT"] = "japan-procedures-test"

from backend.services.query import query_agent
from backend.services.context import set_user_context

# Set context
thread_id = "test-session-123"
set_user_context(thread_id, "work", "Tokyo")

# Make multiple queries
query_agent("How do I renew my visa?", thread_id)
query_agent("What documents do I need?", thread_id)
query_agent("Where is the immigration office?", thread_id)

# Check LangSmith:
# - All 3 traces should appear
# - They share the same thread_id in metadata
# - You can see the full conversation flow
```

### Test 3: Custom Metadata

```python
from backend.services.query import query_agent

# The thread_id and metadata are automatically included in traces
result = query_agent("Test question", thread_id="test-456")

# In LangSmith, you'll see:
# - Metadata: visa_type, location, query_type
# - Tags: japan-procedures, conversation, etc.
# - Full state at each checkpoint
```

## LangSmith Features for Testing

### 1. Trace Comparison

Compare multiple runs side-by-side:

```python
# Run 1: Original parameters
result1 = query_agent("How do I get a visa?", "test-A")

# Run 2: Different context
set_user_context("test-B", "student", "Osaka")
result2 = query_agent("How do I get a visa?", "test-B")

# In LangSmith:
# - Select both traces
# - Click "Compare"
# - See differences in execution, timing, outputs
```

### 2. Playground

Modify and replay any trace:

1. Open a trace in LangSmith
2. Click **"Open in Playground"**
3. Edit prompts, parameters, or inputs
4. Re-run with modifications
5. Compare results

### 3. Datasets

Create test datasets from real traces:

```python
# In LangSmith UI:
# 1. Select traces
# 2. Click "Add to Dataset"
# 3. Create dataset: "visa-renewal-queries"

# Then run evaluations:
from langsmith import Client

client = Client()

# Get dataset
dataset = client.read_dataset(dataset_name="visa-renewal-queries")

# Run evaluation (compares against expected outputs)
results = client.evaluate(
    lambda inputs: query_agent(inputs["question"], inputs["thread_id"]),
    dataset=dataset,
    evaluators=[...],  # Add custom evaluators
)
```

### 4. Monitoring Dashboards

LangSmith auto-generates dashboards showing:
- Request volume over time
- Latency percentiles (p50, p95, p99)
- Error rates
- Token usage and costs
- Most common queries

## Advanced Configuration

### Custom Project Names per Environment

```bash
# .env.development
LANGCHAIN_PROJECT=japan-procedures-dev

# .env.staging
LANGCHAIN_PROJECT=japan-procedures-staging

# .env.production
LANGCHAIN_PROJECT=japan-procedures-prod
```

### Custom Run Names and Tags

```python
# backend/services/query.py
def query_agent(question: str, thread_id: str) -> dict:
    # ... existing code ...
    
    # Add custom metadata for LangSmith
    import os
    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        # LangSmith automatically picks up these from LangGraph config
        config["metadata"]["run_name"] = f"query-{thread_id}"
        config["metadata"]["tags"] = tags  # Already set for Langfuse
```

### Filtering Sensitive Data

```python
# Hide sensitive data from traces
import os
os.environ["LANGCHAIN_HIDE_INPUTS"] = "true"
os.environ["LANGCHAIN_HIDE_OUTPUTS"] = "true"

# Or filter specific fields
def filter_sensitive_data(data):
    if isinstance(data, dict):
        return {k: "***" if k in ["password", "api_key"] else v 
                for k, v in data.items()}
    return data
```

## Testing Workflows

### Development Workflow

```bash
# 1. Enable LangSmith for development
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=dev-testing

# 2. Run your code
python run_server.py

# 3. Debug in LangSmith
# - View traces in real-time
# - Inspect state at each node
# - Compare different runs
# - Test modifications in playground
```

### Testing Workflow

```python
# test_agent.py
import pytest
from backend.services.query import query_agent
from langsmith import Client

def test_visa_renewal():
    """Test visa renewal queries with LangSmith tracking"""
    # Run query (automatically traced)
    result = query_agent(
        "How do I renew my work visa?",
        thread_id="pytest-visa-renewal"
    )
    
    assert result["answer"]
    assert len(result["citations"]) > 0
    
    # Optionally: Add to dataset for future regression testing
    client = Client()
    client.create_example(
        inputs={"question": "How do I renew my work visa?"},
        outputs={"answer": result["answer"]},
        dataset_name="visa-queries-regression"
    )

def test_multi_turn_conversation():
    """Test multi-turn conversation tracking"""
    thread_id = "pytest-multi-turn"
    
    # Turn 1
    r1 = query_agent("I need to renew my visa", thread_id)
    
    # Turn 2
    r2 = query_agent("What documents?", thread_id)
    
    # Turn 3
    r3 = query_agent("Where do I go?", thread_id)
    
    # In LangSmith: View session with all 3 traces linked by thread_id
    assert all([r1["answer"], r2["answer"], r3["answer"]])
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test with LangSmith

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests with LangSmith tracing
        env:
          LANGCHAIN_TRACING_V2: true
          LANGCHAIN_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          LANGCHAIN_PROJECT: ci-tests-${{ github.run_id }}
        run: pytest tests/
      
      - name: Create dataset from traces
        run: |
          python scripts/export_traces_to_dataset.py \
            --project ci-tests-${{ github.run_id }} \
            --dataset ci-regression-${{ github.sha }}
```

## Troubleshooting

### Traces Not Appearing

```bash
# Check environment variables
echo $LANGCHAIN_TRACING_V2
echo $LANGCHAIN_API_KEY

# Should output:
# true
# lsv2_pt_...

# Test connection
python -c "from langsmith import Client; Client().list_projects()"
```

### Verify Installation

```bash
# Check if langsmith is installed
pip show langsmith

# Should show version >= 0.1.0
```

### Network Issues

```bash
# Check if you can reach LangSmith
curl -H "x-api-key: $LANGCHAIN_API_KEY" \
  https://api.smith.langchain.com/info

# Should return: {"version": "..."}
```

## Comparison: LangSmith vs Langfuse

### When to Use LangSmith

✅ **Use LangSmith for:**
- Debugging LangGraph execution
- Interactive testing in playground
- Dataset creation and evaluation
- Comparing multiple runs
- Native LangChain integration

### When to Use Langfuse

✅ **Use Langfuse for:**
- Production monitoring with sessions
- User journey analysis
- Custom tagging and categorization
- Multi-vendor LLM tracking
- Cost analysis across providers

### Best Practice: Use Both!

```bash
# .env for production
# Enable both for comprehensive observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
```

**Result:**
- LangSmith: Automatic traces for all LangChain ops
- Langfuse: Session-based tracking with custom tags
- Complete observability from both perspectives

## Cost Considerations

### LangSmith Pricing

- **Free Tier**: 5,000 traces/month
- **Plus**: $39/month for 50,000 traces
- **Enterprise**: Custom pricing

### Trace Optimization

```bash
# Only trace in development/staging
LANGCHAIN_TRACING_V2=${{ env.ENVIRONMENT != 'production' }}

# Or sample in production (10% of requests)
LANGCHAIN_SAMPLING_RATE=0.1
```

## Resources

- [LangSmith Documentation](https://docs.smith.langchain.com)
- [LangGraph + LangSmith](https://langchain-ai.github.io/langgraph/concepts/tracing/)
- [LangSmith Python Client](https://github.com/langchain-ai/langsmith-sdk)
- [Evaluation Guide](https://docs.smith.langchain.com/evaluation)

## Quick Reference

```bash
# Enable LangSmith
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_pt_your-key
export LANGCHAIN_PROJECT=your-project-name

# Disable LangSmith
export LANGCHAIN_TRACING_V2=false

# Test connection
python -c "from langsmith import Client; print(Client().info())"

# View traces
# https://smith.langchain.com/your-org/projects/your-project-name
```

---

**You now have dual observability:**
- 🔍 **LangSmith**: Deep LangGraph debugging
- 📊 **Langfuse**: Production session analytics

Both work together seamlessly! 🎉

