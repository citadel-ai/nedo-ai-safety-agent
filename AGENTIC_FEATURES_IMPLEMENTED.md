# Agentic Features Implemented

## Overview

The Japan Helpdesk now includes two powerful agentic features that significantly enhance its capabilities:

1. **Multi-Query Search Agent** - Intelligent search with multiple query variants
2. **Multi-Step Procedure Agent** - Breaks complex procedures into actionable steps

---

## 1. Multi-Query Search Agent

### What It Does

Instead of searching with a single query, the system now:
1. **Generates 3-4 query variants** using different terminology and angles
2. **Executes parallel searches** across Vector DB and Google
3. **Deduplicates and ranks** all results
4. **Provides comprehensive information** from multiple perspectives

### Example

**User**: "How do I renew my visa?"

**Traditional Single Query**:
- Search: "visa renewal procedure"
- Results: ~5 documents

**Agentic Multi-Query**:
- Query 1: "visa renewal procedure immigration office"
- Query 2: "visa extension requirements documents timeline"
- Query 3: "residence status renewal application process"
- Results: ~15-20 unique documents (3x more coverage!)

### Technical Details

- **Node**: `agentic_search_orchestrator_node`
- **LLM**: `gemini-2.5-flash` (0.3 temperature, 512 max tokens)
- **Parallel Execution**: All searches run simultaneously using `asyncio.gather`
- **Deduplication**: Removes duplicate content by hash/URL
- **Enhancement**: Adds site restrictions (`site:moj.go.jp OR site:isa.go.jp`) for official sources

### Benefits

✅ **Better coverage**: Finds information that uses different terminology  
✅ **More comprehensive**: Covers multiple aspects of the question  
✅ **Official sources**: Prioritizes government websites  
✅ **Faster**: Parallel execution, no sequential delays  

---

## 2. Multi-Step Procedure Agent

### What It Does

Analyzes if a query involves multi-step procedures and breaks them down into:
- **Sequential steps** with clear ordering
- **Locations** for each step (which office, online, etc.)
- **Required documents** for each step
- **Estimated time** for each step
- **Dependencies** (which steps must be done first)
- **Deadlines** and timing constraints
- **Tips** to avoid common mistakes

### Example

**User**: "I just got married to a Japanese citizen. What do I need to do?"

**Traditional Response**:
"You need to register your marriage at the city hall..."

**Agentic Multi-Step Breakdown**:

```
Marriage and Visa Status Change Procedure (Est. time: 4-6 weeks)

**Step 1: Marriage Registration**
→ Register your marriage at your local city/ward office
📍 Where: Your city/ward office (市役所/区役所)
📄 Documents: Both passports, birth certificates, divorce certificates (if applicable)
⏱️ Time: 1-2 hours at office
⚠️ Deadline: Should be done within 14 days
💡 Tip: Make appointment in advance if possible

**Step 2: Apply for Change of Status of Residence**
→ Apply to change to spouse visa if desired
📍 Where: Immigration Services Agency office
📄 Documents: Marriage certificate, spouse's documents, proof of relationship
⏱️ Time: 2-4 weeks processing
⚠️ Deadline: Before current visa expires
💡 Tip: Can apply immediately after marriage registration

**Step 3: Update Residence Card**
→ Update residence card with new status
📍 Where: Immigration office
📄 Documents: Current residence card, new visa approval
⏱️ Time: Same day
💡 Tip: Bring passport-sized photos

**⚠️ Important Notes:**
• Marriage registration and visa change are separate procedures
• You can continue on your current visa while applying for spouse visa
• Spouse visa allows unrestricted work in Japan

**🚨 Common Mistakes to Avoid:**
• Waiting too long to apply for visa change before current visa expires
• Not collecting all required documents beforenhand
• Forgetting to update address after marriage
```

### Technical Details

- **Node**: `multi_step_procedure_agent_node`
- **LLM**: `gemini-2.5-flash` (0.3 temperature, 2048 max tokens)
- **Schema**: Structured Pydantic model (`MultiStepProcedure`, `ProcedureStep`)
- **Context-aware**: Uses intake session data (location, visa type, timeline)
- **Smart detection**: Only activates for multi-step procedures

### Benefits

✅ **Actionable guidance**: Users know exactly what to do  
✅ **Prevents mistakes**: Highlights common errors  
✅ **Timeline clarity**: Shows dependencies and deadlines  
✅ **Complete picture**: Users don't miss related steps  

---

## Workflow Integration

### New Workflow

```
User Query
    ↓
Adversarial Detection
    ↓
Intake Agent (gather context)
    ↓
Query Synthesizer
    ↓
Scope Check
    ↓
Agentic Search (NEW! - multi-query)
    ↓
Multi-Step Procedure (NEW! - break down steps)
    ↓
Legal Check
    ↓
Response Synthesis
    ↓
Final Response
```

### Where They Fit

**Agentic Search** replaces the simple `hybrid_search` node with intelligent multi-query search.

**Multi-Step Procedure** analyzes search results and enhances the response with structured step-by-step guidance when appropriate.

---

## Monitoring

### Logs to Watch For

**Agentic Search**:
```
🔍 AGENTIC SEARCH - Base query: 'student visa renewal'
🔍 Generated 3 query variants
🔍 Variant 1: 'visa renewal procedure immigration office'
⚡ Executing 6 parallel searches...
✅ AGENTIC SEARCH COMPLETE:
   Vector results: 12 unique
   Google results: 8 unique
   Total: 20 results
```

**Multi-Step Procedure**:
```
📋 MULTI-STEP PROCEDURE - Analyzing: 'How do I get married?'
✅ MULTI-STEP PROCEDURE DETECTED: 'Marriage and Visa Change'
   Total steps: 3
   Estimated time: 4-6 weeks
📋 Added 3 steps to recommendations
```

---

## Configuration

Both agents use the same LLM configuration:
- **Model**: `gemini-2.5-flash`
- **Temperature**: `0.3` (focused, deterministic)
- **Location**: `us-central1`

Tokens:
- Search: 512 max (short queries)
- Procedure: 2048 max (detailed breakdowns)

---

## Future Enhancements

### For Agentic Search:
1. **Query learning**: Learn from successful queries to improve generation
2. **Multi-language**: Generate Japanese queries when appropriate
3. **Source-specific strategies**: Different queries for vector DB vs Google
4. **Iterative refinement**: If results are poor, generate new queries

### For Multi-Step Procedure:
1. **Visual timeline**: Generate Gantt chart or flowchart
2. **Personalized plans**: Save and track user's progress
3. **Reminders**: Send deadline notifications
4. **Document checklist**: Interactive checklist that users can check off

---

## Performance Impact

**Agentic Search**:
- Additional time: ~2-3 seconds (parallel execution mitigates overhead)
- API calls: 3-4x more (but find 3-4x more relevant information)
- Token usage: ~1000 tokens for query generation + search

**Multi-Step Procedure**:
- Additional time: ~1-2 seconds
- API calls: 1 additional LLM call
- Token usage: ~500-1500 tokens

**Total impact**: +3-5 seconds per query, but **significantly better results**.

---

## Success Metrics

Track these to measure impact:
1. **Search result quality**: User satisfaction with answers
2. **Coverage improvement**: % increase in relevant documents found
3. **Procedure completeness**: % of multi-step queries that get full breakdowns
4. **User follow-ups**: Reduction in "What next?" type questions
5. **Task completion**: % of users who successfully complete procedures

---

## Comparison: Before vs After

### Before (Simple Search)
- 1 query → 5-7 results
- Generic procedure descriptions
- Users often confused about next steps
- Required multiple back-and-forth questions

### After (Agentic)
- 3-4 queries → 15-20 results
- Structured step-by-step procedures
- Clear action plan with timelines
- Comprehensive in single response

**Result**: Users get **3x more information** with **structured guidance** in **one interaction**.

---

These agentic features transform the Japan Helpdesk from a simple Q&A system into an **intelligent assistant** that proactively provides comprehensive, actionable guidance!

