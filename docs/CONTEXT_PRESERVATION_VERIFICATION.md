# Context Preservation Verification ✅

## 🧪 Test Results - Context Successfully Preserved!

### Test Scenario:
```
1. User: "How do I get a my number card?"
2. Agent: "Which city are you in?"
3. User: "Tokyo" (quick-reply)
4. Agent: "What type of visa?"
5. User: "Student" (quick-reply)
6. Agent: Should provide My Number card info (NOT Student Visa info)
```

### ✅ **Test Result: PASSED**

```
🔍 Final Response Analysis:
======================================================================
✅ Contains My Number card keywords: True
❌ Contains Student Visa MAIN keywords: False

✅ ✅ ✅ CONTEXT PRESERVED CORRECTLY! ✅ ✅ ✅
The response is about My Number card (as expected)
======================================================================
```

---

## 📊 What Was Fixed

### Before Fix:
- **User asks**: "How do I get a My Number card?"
- **User answers**: "Tokyo" → "Student" (via quick-replies)
- **System responds with**: "Student Visa and Initial Residency Setup" ❌ **WRONG!**

### After Fix:
- **User asks**: "How do I get a My Number card?"
- **User answers**: "Tokyo" → "Student" (via quick-replies)
- **System responds with**: "Obtaining a My Number Card (Individual Number Card)" ✅ **CORRECT!**

---

## 🔧 Two-Part Fix Applied

### Part 1: Intake Agent - Preserve `main_request` Across Turns

**File**: `app/nodes/intake_agent.py`

#### 1.1: Set Initial `main_request` (Lines 179-187)
```python
# CRITICAL: Set main_request on first interaction if not already set
if not session.collected_info or "main_request" not in session.collected_info:
    if not session.collected_info:
        session.collected_info = {}
    session.collected_info["main_request"] = state["user_input"]
    logger.info(f"🔵 INTAKE AGENT - Set initial main_request: '{state['user_input']}'")
```

**Why**: Capture the user's original question before any follow-up interactions.

#### 1.2: Preserve `main_request` After LLM Updates (Lines 236-244)
```python
# CRITICAL: Preserve main_request from original session if it exists
# The LLM might not always include it in collected_info when processing follow-ups
if session.collected_info and "main_request" in session.collected_info:
    if not updated_session.collected_info:
        updated_session.collected_info = {}
    # Only preserve if the LLM didn't explicitly update it
    if "main_request" not in updated_session.collected_info:
        updated_session.collected_info["main_request"] = session.collected_info["main_request"]
        logger.info(f"🔵 INTAKE AGENT - Preserved main_request: '{session.collected_info['main_request']}'")
```

**Why**: When the LLM generates an updated `IntakeSession`, it may omit `main_request` from `collected_info`, thinking it's redundant. This code ensures it's always preserved.

---

### Part 2: Multi-Step Procedure Agent - Use `main_request` Instead of Latest Input

**File**: `app/nodes/multi_step_procedure_agent.py` (Lines 101-111)

```python
# Get user query - use main_request from intake if available to avoid using quick-reply answers
intake = state.get("intake_session")
user_query = state["user_input"]

# Prefer the original main request over the latest user input (which might be a quick-reply answer)
if intake and hasattr(intake, 'collected_info') and intake.collected_info:
    main_request = intake.collected_info.get("main_request")
    if main_request:
        user_query = main_request
        logger.info(f"📋 Using original main_request: '{main_request}' instead of latest input: '{state['user_input']}'")
```

**Why**: The Multi-Step Procedure Agent analyzes the user's question to generate step-by-step guidance. Using the latest input ("Student") would be wrong - we need the original question ("How do I get a My Number card?").

---

## 🎯 How Context Flows Through the System

### Turn 1: Initial Question
```
User Input: "How do I get a my number card?"
↓
Intake Agent:
  - Creates new session
  - Sets collected_info["main_request"] = "How do I get a my number card?"
  - Asks: "Which city are you in?"
↓
State:
  {
    "user_input": "How do I get a my number card?",
    "intake_session": {
      "collected_info": {
        "main_request": "How do I get a my number card?"  ← STORED!
      }
    }
  }
```

### Turn 2: Quick-Reply Answer (Location)
```
User Input: "Tokyo (東京)"
↓
Intake Agent:
  - Loads existing session
  - LLM generates updated session with location
  - **CODE PRESERVES main_request** (LLM might have omitted it)
  - Asks: "What type of visa?"
↓
State:
  {
    "user_input": "Tokyo (東京)",
    "intake_session": {
      "collected_info": {
        "main_request": "How do I get a my number card?",  ← PRESERVED!
        "location": "Tokyo"
      }
    }
  }
```

### Turn 3: Quick-Reply Answer (Visa Type)
```
User Input: "Student (留学)"
↓
Intake Agent:
  - Loads existing session
  - LLM generates updated session with visa type
  - **CODE PRESERVES main_request** (LLM might have omitted it)
  - Marks is_complete = True
↓
Query Synthesizer:
  - Uses synthesized_search_query or main_request
↓
Multi-Step Procedure Agent:
  - **Uses main_request** instead of user_input
  - Analyzes: "How do I get a my number card?" (NOT "Student")
  - Generates: "Obtaining a My Number Card" procedure ✅
↓
State:
  {
    "user_input": "Student (留学)",
    "intake_session": {
      "collected_info": {
        "main_request": "How do I get a my number card?",  ← STILL PRESERVED!
        "location": "Tokyo",
        "visa_type": "Student"
      }
    }
  }
```

---

## 🧪 Test Commands

### Quick Test:
```bash
# Terminal 1: Backend should be running
cd /Users/tapatun/adk-samples/japan-helpdesk-deployable
uv run uvicorn app.server:app --reload --port 8080

# Terminal 2: Run test
# Step 1
curl -s -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I get a my number card?", "user_id": "test_ctx", "session_id": null}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Session: {d[\"session_id\"]}'); print(f'Response: {d[\"response\"][:100]}')"

# Step 2 (use the session_id from above)
curl -s -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tokyo", "user_id": "test_ctx", "session_id": "session_XXXXX"}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Response: {d[\"response\"][:100]}')"

# Step 3 (use the same session_id)
curl -s -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Student", "user_id": "test_ctx", "session_id": "session_XXXXX"}' \
  > /tmp/response.json

# Check result
python3 << 'EOF'
import json
with open('/tmp/response.json', 'r') as f:
    data = json.load(f)
response = data.get('response', '').lower()
has_mynumber = 'my number card' in response or 'individual number card' in response
has_visa = 'certificate of eligibility' in response or 'coe' in response
print(f"✅ About My Number card: {has_mynumber}")
print(f"❌ About Student Visa: {has_visa}")
if has_mynumber and not has_visa:
    print("✅ ✅ ✅ CONTEXT PRESERVED! ✅ ✅ ✅")
EOF
```

---

## 📝 Key Learnings

### Problem: LLM Context Loss in Multi-Turn Conversations
When an LLM generates structured output (like an updated `IntakeSession`), it may:
- Focus on the **new information** (location, visa type)
- **Omit fields** it considers redundant (like `main_request`)
- Return a valid but **incomplete** JSON structure

### Solution: Explicit State Preservation
Don't rely on the LLM to preserve all context fields. Instead:
1. **Capture critical fields early** (on first interaction)
2. **Explicitly preserve them** after each LLM update
3. **Use preserved fields** in downstream agents

### Best Practice:
```python
# After parsing LLM response:
if original_session.critical_field and not updated_session.critical_field:
    updated_session.critical_field = original_session.critical_field
```

---

## 🎯 Impact

### UX Improvement:
- ✅ Users can use quick-reply buttons without losing context
- ✅ Multi-turn conversations work correctly
- ✅ System maintains the original question throughout the conversation

### Technical Improvement:
- ✅ Robust state management across LLM updates
- ✅ Explicit preservation of critical context fields
- ✅ Prevents context loss in multi-agent workflows

---

**Status**: ✅ **FIXED AND VERIFIED**  
**Date**: 2025-10-03  
**Test Result**: Context successfully preserved across 3-turn conversation with quick-replies

