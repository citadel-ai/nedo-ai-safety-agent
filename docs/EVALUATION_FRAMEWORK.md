# Agent Evaluation Framework

## Overview

This document describes the comprehensive evaluation framework implemented for the Japan Procedures Agent, following enterprise best practices from Dataiku's ["Evaluating AI Agents Effectively for Enterprise Use"](https://blog.dataiku.com/evaluating-ai-agents-effectively-for-enterprise-use).

The framework focuses on **Safety & Compliance** and **Task Quality & Accuracy** as primary concerns for pilot deployment with real users.

## Architecture

### Components

```
backend/evaluation/
├── safety.py          # PII detection, content safety
├── quality.py         # Accuracy scoring, task completion
├── metrics.py         # Performance tracking, cost monitoring
├── audit.py           # Enhanced audit logging
├── benchmarks.py      # Gold-standard test cases
└── alerts.py          # Real-time alerting

backend/middleware/
├── pii_filter.py      # Request/response PII filtering
├── metrics.py         # Latency/cost tracking middleware
└── safety.py          # Response safety checks

data/benchmarks/
├── gold_standard.json # SME-created benchmarks
└── schema.json        # Benchmark format specification
```

### Integration Points

1. **LangGraph Nodes**: Evaluation hooks in `search_answer.py` and other nodes
2. **FastAPI Middleware**: Automatic safety/performance checks
3. **Langfuse**: Unified observability with evaluation metrics
4. **Agent State**: Evaluation fields in `AgentState`

---

## Category 1: Safety & Compliance

### 1.1 PII Detection

**Module**: `backend/evaluation/safety.py`

**Detects**:
- Email addresses
- Phone numbers (Japanese and international)
- My Number (マイナンバー) - 12-digit Japanese ID
- Passport numbers
- Japanese addresses (keyword-based)
- Credit card numbers
- Bank account numbers

**Configuration**:
```env
PII_DETECTION_ENABLED=true
PII_MASKING_MODE=log_only  # or 'mask_output'
```

**Usage**:
```python
from backend.evaluation.safety import PIIDetector

detector = PIIDetector()
result = detector.detect_pii(text)

if result.has_pii:
    print(f"Found {len(result.matches)} PII instances")
    print(f"Risk level: {result.risk_level}")
```

**Risk Levels**:
- **High**: My Number, passport, credit card, bank account
- **Medium**: Multiple PII instances
- **Low**: Single low-risk PII (e.g., email only)

### 1.2 Content Safety

**Module**: `backend/evaluation/safety.py`

**Checks**:
- Toxic/harmful content (keyword-based)
- Biased language
- Hallucination risk (low citation coverage)
- Misinformation indicators

**Configuration**:
```env
SAFETY_SCORE_THRESHOLD=0.80
MIN_CITATION_COVERAGE=0.70
```

**Scoring**:
```python
safety_score = (
    (1.0 - toxicity_score) * 0.4 +
    (1.0 - bias_score) * 0.3 +
    citation_coverage * 0.3
)
```

### 1.3 Audit Logging

**Module**: `backend/evaluation/audit.py`

**Logs**:
- All LLM decisions (scope check, fact extraction)
- Tool invocations with parameters
- Session lifecycle events
- Safety violations
- User actions (feedback, fact deletion)

**Output**:
- `logs/audit.log` - JSON-formatted events
- Langfuse events with tag `"audit"`

**Example**:
```python
from backend.evaluation.audit import get_audit_logger

audit_logger = get_audit_logger()
audit_logger.log_query(thread_id, query, metadata)
audit_logger.log_safety_violation(thread_id, violation_type, details)
```

### 1.4 Alerts

**Module**: `backend/evaluation/alerts.py`

**Alert Types**:
- High latency (> 5000ms)
- High cost (> $0.10/query)
- High error rate (> 5%)
- Safety violations
- PII detected (medium/high risk)
- Low quality responses

**Channels**:
- `logs/alerts.log`
- Langfuse events
- In-memory (accessible via API)

**API**:
```bash
GET /api/alerts/active?severity=error
GET /api/alerts/summary
```

---

## Category 2: Task Quality & Accuracy

### 2.1 Quality Scoring

**Module**: `backend/evaluation/quality.py`

**Automatic Metrics**:
1. **Citation Coverage** (40%): % of answer grounded in citations
2. **LLM Confidence** (30%): From Vertex AI response
3. **Completeness** (30%): Did answer address query?

**Manual Metrics**:
- SME rating (1-5 scale) if available

**Formula**:
```python
auto_score = (
    citation_coverage * 0.4 +
    llm_confidence * 0.3 +
    completeness * 0.3
)

# With SME rating
final_score = (auto_score * 0.4) + (sme_rating_normalized * 0.6)
```

**Configuration**:
```env
QUALITY_SCORE_THRESHOLD=0.75
```

### 2.2 Task Completion Tracking

**Module**: `backend/evaluation/quality.py`

**Indicators**:
- No error occurred
- In-scope response
- Substantial content (> 100 chars)
- Not a follow-up prompt

**Tracked in State**:
```python
class AgentState:
    task_completed: bool
    completion_quality: float  # 0-1
    requires_followup: bool
```

### 2.3 Benchmarks

**Module**: `backend/evaluation/benchmarks.py`

**Structure** (`data/benchmarks/gold_standard.json`):
```json
{
  "id": "visa-renewal-001",
  "query": "How do I renew my work visa?",
  "context": {"visa_type": "Work Visa", "location": "Tokyo"},
  "expected_answer_elements": [
    "apply 3 months before expiration",
    "immigration office",
    "required documents"
  ],
  "must_include_citations": true,
  "category": "visa-renewal",
  "created_by": "sme@example.com"
}
```

**API**:
```bash
POST /api/benchmarks/create    # Create benchmark (SME)
GET  /api/benchmarks/list      # List benchmarks
GET  /api/benchmarks/results   # Historical results
```

**Usage**:
```python
from backend.evaluation.benchmarks import get_benchmark_manager

manager = get_benchmark_manager()
benchmark = manager.create_benchmark(
    query="How do I renew my visa?",
    context={"visa_type": "Work Visa"},
    expected_answer_elements=[...],
    category="visa-renewal",
    created_by="sme@example.com"
)
```

### 2.4 Error Tracking

**Module**: `backend/evaluation/metrics.py`

**Metrics**:
- Total queries
- Success rate
- Out-of-scope rate
- Context drift rate
- API errors
- Timeouts

**Access**:
```bash
GET /api/metrics/realtime  # Current metrics
GET /api/metrics/nodes     # Per-node performance
```

---

## Category 3: Operational Performance

### 3.1 Latency Tracking

**Module**: `backend/evaluation/metrics.py`, `backend/middleware/metrics.py`

**Tracked**:
- End-to-end request latency
- Per-node latency breakdown
- Percentiles (p50, p95, p99)

**Middleware**: Automatically tracks all `/api/*` endpoints

**Alerts**: Latency > 5000ms triggers alert

### 3.2 Cost Estimation

**Module**: `backend/evaluation/metrics.py`

**Pricing** (approximate):
```python
VERTEX_AI_SEARCH_COST_PER_QUERY = $0.005
GEMINI_INPUT_COST_PER_1K_TOKENS = $0.0001
GEMINI_OUTPUT_COST_PER_1K_TOKENS = $0.0003
```

**Alerts**: Cost > $0.10/query triggers alert

---

## Category 4: User Feedback

### 4.1 Feedback API

**Endpoints**:

**Rating** (1-5 stars):
```bash
POST /api/feedback/rating
{
  "thread_id": "...",
  "query": "...",
  "rating": 4,
  "comment": "Very helpful!"
}
```

**Flag incorrect**:
```bash
POST /api/feedback/flag
{
  "thread_id": "...",
  "query": "...",
  "reason": "incorrect_information",
  "details": "The deadline is wrong"
}
```

---

## Configuration

### Environment Variables

```env
# Safety & Compliance
PII_DETECTION_ENABLED=true
PII_MASKING_MODE=log_only
SAFETY_SCORE_THRESHOLD=0.80

# Quality
BENCHMARK_MODE=enabled
MIN_CITATION_COVERAGE=0.70
QUALITY_SCORE_THRESHOLD=0.75

# Monitoring
METRICS_ENABLED=true
LATENCY_ALERT_THRESHOLD_MS=5000
COST_ALERT_THRESHOLD_USD=0.10
```

---

## Integration with Langfuse

All evaluation metrics are logged to Langfuse for unified observability:

```python
# In query service
config["metadata"] = {
    "langfuse_session_id": thread_id,
    "langfuse_tags": ["japan-procedures", "evaluation"],
    "evaluation_enabled": True,
}

# After evaluation
client.event(
    name="evaluation_metrics",
    metadata={
        "quality_score": 0.85,
        "safety_score": 0.92,
        "task_completed": True,
        "citations_count": 3
    },
    session_id=thread_id
)
```

---

## Success Metrics

### Safety & Compliance
- ✅ Zero PII leaks in logs/responses
- ✅ 100% of queries logged with audit trail
- ✅ < 1% safety violations
- ✅ < 5% high-risk PII detections

### Task Quality & Accuracy
- ✅ > 90% task completion rate
- ✅ > 0.85 average quality score
- ✅ > 95% benchmark pass rate
- ✅ < 0.70 citation coverage flags for review

### Operational
- ✅ < 3s p95 latency
- ✅ 99.5% uptime
- ✅ < $0.05 cost per query

### User Satisfaction
- ✅ > 4.0/5.0 average rating
- ✅ < 10% negative feedback rate
- ✅ > 60% repeat usage rate

---

## Monitoring Dashboard

Access real-time metrics via API:

```bash
# System health
GET /api/metrics/realtime
{
  "latency": {"p50": 1234, "p95": 2456, "p99": 3456},
  "errors": {"success_rate": 0.94, "error_rate": 0.06},
  "cost": {"total_usd": 12.50, "avg_per_query": 0.025},
  "health": "healthy"
}

# Active alerts
GET /api/alerts/summary
{
  "total_alerts": 5,
  "unacknowledged": 2,
  "by_severity": {"warning": 3, "error": 2}
}
```

---

## Best Practices

1. **Review alerts daily**: Check `/api/alerts/active` for safety/quality issues
2. **Monitor metrics weekly**: Track trends in `/api/metrics/realtime`
3. **Run benchmarks regularly**: Nightly runs to catch regressions
4. **Audit logs for compliance**: Review `logs/audit.log` for sensitive operations
5. **Collect user feedback**: Integrate rating/flag buttons in UI
6. **SME involvement**: Have SMEs create benchmarks and review flagged responses

---

## Troubleshooting

### High PII Detection Rate
- Review `logs/audit.log` for patterns
- Check if users are submitting personal data in queries
- Consider adding user guidance to avoid PII

### Low Quality Scores
- Check citation coverage (may need better data)
- Review completeness issues (queries not fully answered)
- Run benchmarks to identify systematic issues

### High Latency
- Check `/api/metrics/nodes` for bottlenecks
- Review Vertex AI Search response times
- Consider caching strategies

### Cost Overruns
- Monitor `/api/metrics/realtime` cost metrics
- Review token usage per query
- Optimize prompts to reduce tokens

---

## Related Documentation

- [SME Review Guide](SME_REVIEW_GUIDE.md) - How SMEs can review and improve the system
- [Safety Compliance](SAFETY_COMPLIANCE.md) - Detailed safety measures
- [Langfuse Best Practices](LANGFUSE_BEST_PRACTICES.md) - Observability setup

---

## References

- [Dataiku Article: Evaluating AI Agents](https://blog.dataiku.com/evaluating-ai-agents-effectively-for-enterprise-use)
- [Langfuse Documentation](https://langfuse.com/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

