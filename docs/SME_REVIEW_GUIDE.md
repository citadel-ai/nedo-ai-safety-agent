# SME Review Guide

## Introduction

This guide is for Subject Matter Experts (SMEs) who are responsible for reviewing and improving the Japan Procedures Agent's quality and accuracy.

As an SME, you play a critical role in:
- Creating gold-standard benchmark test cases
- Reviewing agent responses for accuracy
- Providing feedback on flagged responses
- Ensuring compliance with procedures and regulations

---

## Getting Started

### Prerequisites

- Access to the system API or admin dashboard
- Understanding of Japanese official procedures
- Basic familiarity with REST APIs (or use provided scripts)

### Tools Available

1. **Benchmark Management API**: Create and manage test cases
2. **Feedback Review API**: Review user-flagged responses
3. **Audit Logs**: Review system decisions and safety events
4. **Metrics Dashboard**: Monitor quality trends

---

## Creating Benchmarks

### What is a Benchmark?

A benchmark is a "gold standard" test case that defines:
- A specific user query
- The expected answer elements
- Required quality criteria (e.g., must include citations)

### Why Create Benchmarks?

- **Regression Testing**: Catch quality degradation
- **Coverage**: Ensure all important topics are handled well
- **Training**: Help improve the system over time

### How to Create a Benchmark

#### Via API

**Endpoint**: `POST /api/benchmarks/create`

**Request**:
```json
{
  "query": "How do I renew my work visa in Tokyo?",
  "context": {
    "visa_type": "Work Visa",
    "location": "Tokyo"
  },
  "expected_answer_elements": [
    "apply 3 months before expiration",
    "immigration office in Tokyo",
    "required documents: passport, residence card, application form",
    "processing time 2-4 weeks"
  ],
  "must_include_citations": true,
  "category": "visa-renewal",
  "created_by": "your.email@example.com",
  "tags": ["visa", "renewal", "tokyo", "work"],
  "notes": "Critical information for work visa holders. Must be accurate."
}
```

**Response**:
```json
{
  "id": "visa-renewal-003",
  "status": "created",
  "message": "Benchmark created successfully"
}
```

#### Via Python Script

```python
import requests

API_BASE = "http://localhost:8000"

def create_benchmark(query, context, expected_elements, category, email):
    response = requests.post(
        f"{API_BASE}/api/benchmarks/create",
        json={
            "query": query,
            "context": context,
            "expected_answer_elements": expected_elements,
            "category": category,
            "created_by": email,
            "must_include_citations": True
        }
    )
    return response.json()

# Example usage
benchmark = create_benchmark(
    query="What documents do I need for residence registration?",
    context={"visa_type": "Student Visa", "location": "Osaka"},
    expected_elements=[
        "residence card (在留カード)",
        "passport",
        "within 14 days of moving",
        "city hall or ward office"
    ],
    category="residence-registration",
    email="sme@example.com"
)
print(f"Created benchmark: {benchmark['id']}")
```

### Best Practices for Benchmarks

#### 1. Be Specific

❌ **Bad**: "Must mention documents"  
✅ **Good**: "Must mention: passport, residence card, application form, photo"

#### 2. Cover Critical Facts

Focus on:
- **Deadlines**: "within 14 days", "3 months before expiration"
- **Required documents**: Specific list
- **Locations**: Office addresses, websites
- **Fees**: Exact costs
- **Important warnings**: Common mistakes to avoid

#### 3. Test Edge Cases

- Unusual visa types
- Special circumstances (married, changing jobs, etc.)
- Regional differences (Tokyo vs. Osaka)
- Recent policy changes

#### 4. Organize by Category

Suggested categories:
- `visa-renewal`
- `visa-change`
- `residence-registration`
- `health-insurance`
- `tax-procedures`
- `bank-account`
- `driver-license`

#### 5. Add Context Notes

```json
{
  "notes": "Critical: This procedure changed in April 2025. Previous answers mentioning old form are incorrect."
}
```

---

## Reviewing Benchmark Results

### Viewing Results

**Endpoint**: `GET /api/benchmarks/results?limit=10`

**Response**:
```json
{
  "count": 2,
  "runs": [
    {
      "timestamp": "2025-10-16T10:30:00Z",
      "results": [
        {
          "benchmark_id": "visa-renewal-001",
          "passed": true,
          "score": 0.95,
          "matched_elements": [
            "apply 3 months before expiration",
            "immigration office",
            "required documents"
          ],
          "missing_elements": [],
          "citations_count": 3
        },
        {
          "benchmark_id": "residence-registration-001",
          "passed": false,
          "score": 0.60,
          "matched_elements": [
            "residence card",
            "city hall"
          ],
          "missing_elements": [
            "within 14 days",
            "passport"
          ],
          "citations_count": 2
        }
      ]
    }
  ]
}
```

### What to Look For

**Passing Benchmarks** (score ≥ 0.8):
- ✅ All critical facts present
- ✅ Citations included
- ✅ No major errors

**Failing Benchmarks** (score < 0.8):
- ⚠️ Missing critical facts → Update data sources
- ⚠️ No citations → Check search configuration
- ⚠️ Incorrect information → Urgent correction needed

### Actions on Failures

1. **Review the actual answer**: Check if missing elements are critical
2. **Update benchmark**: If expectations were wrong
3. **Improve data**: If answer source is inadequate
4. **Escalate**: If systematic issue (e.g., all visa renewals failing)

---

## Reviewing User Feedback

### Viewing Flagged Responses

User-flagged responses appear in audit logs:

**File**: `logs/audit.log`

**Filter for**:
```json
{
  "event_type": "flag_response",
  "thread_id": "...",
  "details": {
    "reason": "incorrect_information",
    "details": "The deadline stated is wrong"
  }
}
```

### Review Process

1. **Find the thread**: `GET /api/thread/{thread_id}`
2. **Review conversation history**: See full context
3. **Verify accuracy**: Check against official sources
4. **Determine action**:
   - ✅ Correct → No action needed
   - ⚠️ Minor issue → Note for improvement
   - ❌ Critical error → Create benchmark to prevent recurrence

### Creating Benchmarks from Failures

When you find a critical error:

```python
# Convert user feedback to benchmark
create_benchmark(
    query="The user's original query",
    context=extract_context_from_thread(thread_id),
    expected_elements=[
        "Correct fact 1",
        "Correct fact 2",
        "Correct fact 3"
    ],
    category="determine-category",
    email="your.email@example.com"
)
```

---

## Providing Quality Ratings

### Rating Scale

When reviewing responses, use this scale:

| Rating | Meaning | Criteria |
|--------|---------|----------|
| 5 | Excellent | Perfect answer, comprehensive, well-cited |
| 4 | Good | Mostly correct, minor omissions acceptable |
| 3 | Acceptable | Correct but incomplete or unclear |
| 2 | Poor | Missing critical information or minor errors |
| 1 | Unacceptable | Incorrect information or completely unhelpful |

### Submitting Ratings

**Endpoint**: `POST /api/feedback/rating`

```json
{
  "thread_id": "thread-123",
  "query": "How do I renew my visa?",
  "rating": 4,
  "comment": "Good answer but missing specific deadline information"
}
```

### Rating Guidelines

**Consider**:
- ✅ **Accuracy**: Are facts correct?
- ✅ **Completeness**: Are all important details included?
- ✅ **Citations**: Are sources provided?
- ✅ **Clarity**: Is it easy to understand?
- ✅ **Actionability**: Can user act on this info?

**Don't penalize for**:
- ❌ Style preferences
- ❌ Information user didn't ask for
- ❌ Over-cautiousness (e.g., "Please verify with office")

---

## Monitoring Quality Trends

### Weekly Review

**Endpoint**: `GET /api/metrics/realtime`

**Key Metrics**:
```json
{
  "errors": {
    "success_rate": 0.94,
    "out_of_scope_rate": 0.03,
    "context_drift_rate": 0.02
  }
}
```

**What to Monitor**:
- **Success rate**: Should be > 90%
- **Out-of-scope rate**: Should be < 5%
- **Average quality score**: Should be > 0.85

### Interpreting Trends

**Declining success rate**:
- Check recent benchmark failures
- Review audit logs for systematic errors
- May indicate data source issues

**High out-of-scope rate**:
- Users asking questions outside scope
- May need to expand coverage
- Or improve scope detection

**Low quality scores**:
- Check citation coverage
- Review completeness issues
- May need better prompts or data

---

## Common Scenarios

### Scenario 1: User reports incorrect deadline

**Steps**:
1. Find thread in audit log
2. Verify correct deadline from official source
3. Create benchmark with correct deadline
4. Document in notes: "Common mistake - deadline is X not Y"

### Scenario 2: Benchmark keeps failing

**Steps**:
1. Review benchmark expectations
2. Check if data source has information
3. If data missing → Escalate to add source
4. If expectations too strict → Update benchmark

### Scenario 3: New policy change

**Steps**:
1. Create new benchmark with updated information
2. Update/archive old benchmarks
3. Add note: "Policy changed on [date]"
4. Monitor related benchmarks for impact

---

## Tools & Scripts

### Bulk Benchmark Creation

For creating many benchmarks at once:

```python
import pandas as pd
import requests

# Read from CSV
df = pd.read_csv("benchmarks.csv")

for _, row in df.iterrows():
    create_benchmark(
        query=row['query'],
        context={"visa_type": row['visa_type'], "location": row['location']},
        expected_elements=row['expected_elements'].split(';'),
        category=row['category'],
        email="sme@example.com"
    )
    print(f"Created: {row['query'][:50]}...")
```

### Benchmark Comparison Tool

Compare current results vs. previous run:

```bash
curl http://localhost:8000/api/benchmarks/results?limit=2 | \
  python compare_runs.py
```

---

## Best Practices Summary

### DO
- ✅ Create specific, actionable benchmarks
- ✅ Review flagged responses promptly
- ✅ Provide detailed feedback comments
- ✅ Monitor quality trends weekly
- ✅ Document policy changes in notes
- ✅ Share learnings with team

### DON'T
- ❌ Create duplicate benchmarks
- ❌ Use vague expected elements
- ❌ Ignore systematic failures
- ❌ Rate based on personal style preference
- ❌ Forget to add context/notes

---

## Getting Help

- **Technical Issues**: Contact engineering team
- **Content Questions**: Consult official procedure documentation
- **System Behavior**: Review [EVALUATION_FRAMEWORK.md](EVALUATION_FRAMEWORK.md)

---

## Appendix: API Reference

### Benchmark Endpoints

```bash
POST   /api/benchmarks/create       # Create new benchmark
GET    /api/benchmarks/list         # List all benchmarks
GET    /api/benchmarks/results      # View test results
```

### Feedback Endpoints

```bash
POST   /api/feedback/rating         # Submit rating
POST   /api/feedback/flag           # Flag incorrect response
```

### Metrics Endpoints

```bash
GET    /api/metrics/realtime        # Current metrics
GET    /api/alerts/summary          # Alert summary
```

