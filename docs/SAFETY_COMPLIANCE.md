# Safety & Compliance Guide

## Overview

This document describes the safety and compliance measures implemented in the Japan Procedures Agent to protect user privacy, ensure content safety, and maintain audit trails for governance.

**Primary Goals**:
- Zero PII leaks in logs or responses
- 100% auditability of agent decisions
- Proactive detection of unsafe content
- Compliance with data protection regulations

---

## PII Protection

### What is PII?

Personally Identifiable Information (PII) includes any data that could identify an individual:

**General PII**:
- Email addresses
- Phone numbers
- Passport numbers
- Credit card numbers
- Bank account numbers

**Japanese-Specific PII**:
- My Number (マイナンバー) - 12-digit national ID
- Japanese addresses (住所)
- Residence card numbers

### Detection Mechanism

**Module**: `backend/evaluation/safety.py` - `PIIDetector`

**Detection Methods**:
1. **Regex Patterns**: For structured data (emails, phones, My Number)
2. **Keyword Matching**: For Japanese addresses (都, 道, 府, 県, 市, 区, etc.)
3. **Luhn Algorithm**: For credit card validation
4. **Context Analysis**: For names and sensitive identifiers

### Configuration

```env
# Enable/disable PII detection
PII_DETECTION_ENABLED=true

# What to do when PII is detected
PII_MASKING_MODE=log_only  # Options: 'log_only' or 'mask_output'
```

**Modes**:
- `log_only`: Log PII detection but don't modify content
- `mask_output`: Replace PII with `[REDACTED]` or masked version

### Examples

#### Email Masking
```
Original: user@example.com
Masked:   u***@example.com
```

#### Phone Masking
```
Original: 090-1234-5678
Masked:   ***-***-5678
```

#### My Number Masking
```
Original: 1234-5678-9012
Masked:   [REDACTED]
```

### Risk Levels

PII detections are categorized by risk:

| Risk Level | Types | Action |
|------------|-------|--------|
| **High** | My Number, passport, credit card, bank account | Alert + Audit |
| **Medium** | Multiple PII instances, phone + address | Audit log |
| **Low** | Single email or phone | Audit log |
| **None** | No PII detected | No action |

### Audit Logging

All PII detections are logged:

**Log Entry**:
```json
{
  "event_type": "pii_detected",
  "thread_id": "thread-123",
  "timestamp": "2025-10-16T10:30:00Z",
  "details": {
    "pii_types": ["email", "phone"],
    "risk_level": "medium",
    "location": "request"
  }
}
```

**File**: `logs/audit.log`

---

## Content Safety

### Safety Checks

**Module**: `backend/evaluation/safety.py` - `ContentSafetyChecker`

**Checks Performed**:

#### 1. Toxicity Detection
- Harmful language
- Illegal activity suggestions
- Fraud/scam indicators

**Method**: Keyword matching + frequency analysis

#### 2. Bias Detection
- Discriminatory language
- Nationality/ethnicity biases
- Unfair generalizations

**Method**: Pattern matching on known bias indicators

#### 3. Hallucination Risk
- Claims not supported by citations
- Low citation coverage (<70%)
- Conflicting information

**Method**: Citation coverage analysis

### Safety Scoring

**Formula**:
```python
safety_score = (
    (1.0 - toxicity_score) * 0.4 +
    (1.0 - bias_score) * 0.3 +
    citation_coverage * 0.3
)
```

**Threshold**: 0.80 (configurable via `SAFETY_SCORE_THRESHOLD`)

**Actions**:
- Score < 0.80: Log safety violation + Create alert
- Score < 0.60: Block response (future enhancement)

### Example Safety Check

```python
from backend.evaluation.safety import ContentSafetyChecker

checker = ContentSafetyChecker()
result = checker.check_safety(
    text="Your response text",
    citations=[{"url": "...", "title": "..."}]
)

if not result.is_safe:
    print(f"Safety issues: {result.issues}")
    print(f"Safety score: {result.safety_score}")
```

**Output**:
```
Safety issues: ['Low citation coverage (0.45), possible hallucination']
Safety score: 0.72
```

---

## Audit Trail

### What is Logged?

**All Critical Events**:
1. User queries and agent responses
2. LLM decisions (scope check, fact extraction)
3. Tool invocations (Vertex AI Search, Google Maps)
4. Safety violations (PII, content safety)
5. User actions (feedback, fact deletion)
6. System errors

### Audit Log Format

**Location**: `logs/audit.log`

**Format**: JSON per line

**Example**:
```json
{
  "timestamp": "2025-10-16T10:30:00.123Z",
  "level": "INFO",
  "message": {
    "event_type": "query_received",
    "thread_id": "thread-123",
    "user_id": null,
    "severity": "info",
    "timestamp": "2025-10-16T10:30:00.123Z",
    "details": {
      "query": "How do I renew my visa?",
      "query_length": 23,
      "metadata": {}
    }
  }
}
```

### Audit Events

| Event Type | Severity | Trigger |
|------------|----------|---------|
| `session_start` | INFO | User starts new conversation |
| `session_end` | INFO | User ends conversation |
| `query_received` | INFO | Every user query |
| `response_generated` | INFO | Every agent response |
| `safety_violation` | WARNING | Safety check fails |
| `pii_detected` | WARNING/ERROR | PII found (based on risk) |
| `tool_invocation` | INFO | Any tool called |
| `user_feedback` | INFO | User provides feedback |
| `error` | ERROR | System error |

### Querying Audit Logs

**Using grep**:
```bash
# Find all safety violations
grep '"event_type": "safety_violation"' logs/audit.log

# Find PII detections for specific thread
grep '"thread_id": "thread-123"' logs/audit.log | grep pii_detected

# Find all high-risk PII
grep '"risk_level": "high"' logs/audit.log
```

**Using jq** (JSON processor):
```bash
# Count safety violations by type
cat logs/audit.log | jq -s '[.[] | select(.message.event_type == "safety_violation")] | group_by(.message.details.violation_type) | map({type: .[0].message.details.violation_type, count: length})'

# Get all errors in last hour
cat logs/audit.log | jq 'select(.level == "ERROR") | select(.timestamp > "2025-10-16T09:30:00Z")'
```

---

## Real-Time Alerting

### Alert System

**Module**: `backend/evaluation/alerts.py`

**Alert Types**:
| Type | Trigger | Severity |
|------|---------|----------|
| High Latency | > 5000ms | WARNING |
| High Cost | > $0.10/query | WARNING |
| High Error Rate | > 5% | ERROR |
| Safety Violation | Content safety failure | ERROR |
| PII Detected | Medium/high risk PII | WARNING/ERROR |
| Low Quality | Quality score < 0.75 | WARNING |

### Alert Channels

1. **File**: `logs/alerts.log`
2. **In-Memory**: Accessible via API
3. **Langfuse**: Events with tag `"alert"`

### API Access

```bash
# Get active alerts
GET /api/alerts/active

# Filter by severity
GET /api/alerts/active?severity=error&unacknowledged_only=true

# Get summary
GET /api/alerts/summary
```

**Response**:
```json
{
  "total_alerts": 5,
  "unacknowledged": 2,
  "recent_hour": 3,
  "by_severity": {
    "info": 0,
    "warning": 3,
    "error": 2,
    "critical": 0
  },
  "by_type": {
    "high_latency": 2,
    "safety_violation": 1,
    "pii_detected": 2
  }
}
```

---

## Middleware Protection

### Request/Response Filtering

**Modules**:
- `backend/middleware/pii_filter.py` - PII detection
- `backend/middleware/safety.py` - Content safety
- `backend/middleware/metrics.py` - Performance tracking

### Processing Pipeline

```
Request → PII Check → Route Handler → Safety Check → Response
            ↓                              ↓
         Audit Log                    Audit Log
            ↓                              ↓
        Alert (if needed)             Alert (if needed)
```

### Automatic Actions

**On Request**:
1. Check for PII in user query
2. Log if found
3. Alert if high-risk

**On Response**:
1. Check for PII in agent answer
2. Check content safety
3. Optionally mask PII (if configured)
4. Log all checks
5. Alert on violations

---

## Compliance Features

### GDPR/Data Protection

**Right to be Forgotten**:
```bash
# Delete thread data
DELETE /api/thread/{thread_id}
```

**Data Minimization**:
- Only essential data stored
- PII masked in logs (if configured)
- Truncated text in audit logs

**Auditability**:
- Complete trace of data processing
- User actions logged
- Retention policy: 90 days (configurable)

### Transparency

**User Visibility**:
- Quality scores visible in API response
- Safety checks visible (optional)
- Citation sources always provided

**Operator Visibility**:
- Full audit trail
- Real-time alerts
- Metrics dashboard

---

## Incident Response

### PII Leak

**If PII appears in logs/responses**:

1. **Immediate**:
   - Review `logs/audit.log` for extent
   - Identify affected threads
   - Check if PII was transmitted

2. **Short-term**:
   - Enable `PII_MASKING_MODE=mask_output`
   - Review and update detection patterns
   - Notify affected users (if applicable)

3. **Long-term**:
   - Create benchmark to prevent recurrence
   - Update documentation
   - Conduct training on PII handling

### Safety Violation

**If unsafe content generated**:

1. **Immediate**:
   - Review full conversation context
   - Check citations for accuracy
   - Determine if data source issue

2. **Short-term**:
   - Create benchmark with correct answer
   - Update prompts if needed
   - Review similar queries

3. **Long-term**:
   - Enhance safety filters
   - Add more detection patterns
   - Monitor for recurrence

---

## Monitoring & Maintenance

### Daily Tasks

- [ ] Check `/api/alerts/active` for critical issues
- [ ] Review `logs/alerts.log` for patterns
- [ ] Verify no high-risk PII detections

### Weekly Tasks

- [ ] Review audit log trends
- [ ] Check safety violation patterns
- [ ] Monitor quality score trends
- [ ] Review user feedback

### Monthly Tasks

- [ ] Audit log retention cleanup (> 90 days)
- [ ] Update PII detection patterns
- [ ] Review and update safety thresholds
- [ ] Compliance report generation

---

## Configuration Summary

### Environment Variables

```env
# PII Detection
PII_DETECTION_ENABLED=true
PII_MASKING_MODE=log_only

# Content Safety
SAFETY_SCORE_THRESHOLD=0.80
MIN_CITATION_COVERAGE=0.70

# Monitoring
METRICS_ENABLED=true
LATENCY_ALERT_THRESHOLD_MS=5000
```

### Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Safety Score | < 0.80 | Alert |
| Citation Coverage | < 0.70 | Flag for review |
| PII Risk | High | Alert + Audit |
| Error Rate | > 5% | Alert |
| Latency p95 | > 5000ms | Alert |

---

## Best Practices

### DO
- ✅ Review audit logs regularly
- ✅ Respond to alerts promptly
- ✅ Keep PII detection patterns updated
- ✅ Test safety checks with edge cases
- ✅ Document all incidents
- ✅ Train team on safety procedures

### DON'T
- ❌ Disable PII detection in production
- ❌ Ignore safety violation alerts
- ❌ Store raw PII in logs
- ❌ Skip regular monitoring
- ❌ Modify thresholds without testing

---

## Testing Safety Measures

### PII Detection Test

```python
from backend.evaluation.safety import PIIDetector

detector = PIIDetector()

test_cases = [
    "My email is test@example.com",
    "Call me at 090-1234-5678",
    "My number is 1234-5678-9012",  # My Number
    "I live at 東京都渋谷区..."
]

for text in test_cases:
    result = detector.detect_pii(text)
    print(f"Text: {text[:30]}...")
    print(f"  PII: {result.has_pii}")
    print(f"  Types: {result.pii_types}")
    print(f"  Risk: {result.risk_level}")
```

### Content Safety Test

```python
from backend.evaluation.safety import ContentSafetyChecker

checker = ContentSafetyChecker()

test_answer = "To renew your visa, visit the immigration office."
test_citations = [{"url": "https://...", "title": "..."}]

result = checker.check_safety(test_answer, test_citations)
print(f"Safe: {result.is_safe}")
print(f"Safety Score: {result.safety_score}")
print(f"Issues: {result.issues}")
```

---

## Related Documentation

- [Evaluation Framework](EVALUATION_FRAMEWORK.md) - Complete evaluation system
- [SME Review Guide](SME_REVIEW_GUIDE.md) - Quality review procedures
- [Langfuse Best Practices](LANGFUSE_BEST_PRACTICES.md) - Observability setup

---

## References

- [GDPR Compliance](https://gdpr.eu/)
- [Japanese Privacy Law](https://www.ppc.go.jp/en/)
- [Dataiku AI Safety Article](https://blog.dataiku.com/evaluating-ai-agents-effectively-for-enterprise-use)

