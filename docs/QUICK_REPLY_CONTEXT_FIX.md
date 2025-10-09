# Quick-Reply Context Loss Bug Fix

## 🐛 **The Problem**

When users answered intake questions using quick-reply buttons, the Multi-Step Procedure Agent was analyzing **the quick-reply answer** instead of **the original question**.

### Example Scenario:
1. **User asks**: "How do I get a My Number card?"
2. **Agent asks**: "Which city are you in?"
   - Quick replies: [Tokyo] [Yokohama] [Osaka]
3. **User clicks**: "Tokyo (東京)"
4. **Agent responds with**: Complete guide about **Student Visa setup** ❌ (Wrong!)
   - **Should respond with**: Complete guide about **My Number card** ✅

---

## 🔍 **Root Cause** (Two Issues)

### Issue 1: Multi-Step Agent Using Wrong Input
**File**: `app/nodes/multi_step_procedure_agent.py`  
**Line 103**: `user_query = state["user_input"]`

The agent was using the **latest user input**, which is the quick-reply answer (e.g., "Tokyo (東京)"), not the original question.

### Issue 2: Intake Agent Not Preserving `main_request`
**File**: `app/nodes/intake_agent.py`

When the LLM generated an updated `IntakeSession` for follow-up questions, it would create a new `collected_info` dict **without preserving** the `main_request` field from the previous session.

**Why This Happens**:
- The LLM sees the current `collected_info` in the prompt
- It generates a new `IntakeSession` JSON with updated fields (e.g., `user_location`, `visa_type`)
- But it may **omit** `main_request` from the output, thinking it's redundant
- When we parse this JSON, we get a new `IntakeSession` where `collected_info` only has the new fields
- **Result**: The original question is lost!

### Debug Logs Showing the Issue:
```
Line 520: QUERY SYNTHESIS - Original: 'How do I get a My Number card?', Latest: 'Student (留学)'
Line 767: MULTI-STEP PROCEDURE - Analyzing: 'Student (留学)'  ← Wrong! Using quick-reply
Line 791: ✅ MULTI-STEP PROCEDURE DETECTED: 'Student Visa and Initial Residency Setup in Japan'
```

The agent thought the user was asking about **Student Visa**, not **My Number card**!

---

## ✅ **The Fix** (Two-Part Solution)

### Part 1: Preserve `main_request` in Intake Agent

**File**: `app/nodes/intake_agent.py`  
**Lines 179-187** (Set initial `main_request`)

```python
# Update session with new input
session.conversation_history.append(f"User: {state['user_input']}")

# CRITICAL: Set main_request on first interaction if not already set
if not session.collected_info or "main_request" not in session.collected_info:
    if not session.collected_info:
        session.collected_info = {}
    session.collected_info["main_request"] = state["user_input"]
    logger.info(f"🔵 INTAKE AGENT - Set initial main_request: '{state['user_input']}'")
```

**Lines 236-244** (Preserve `main_request` across LLM updates)

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

### Part 2: Use `main_request` in Multi-Step Procedure Agent

**File**: `app/nodes/multi_step_procedure_agent.py`  
**Lines 101-111**

```python
# Before (WRONG):
user_query = state["user_input"]  # Uses latest input (quick-reply answer)

# After (FIXED):
intake = state.get("intake_session")
user_query = state["user_input"]

# Prefer the original main request over the latest user input
if intake and hasattr(intake, 'collected_info') and intake.collected_info:
    main_request = intake.collected_info.get("main_request")
    if main_request:
        user_query = main_request
        logger.info(f"📋 Using original main_request: '{main_request}' instead of latest input: '{state['user_input']}'")
```

### How It Works:
1. **First message**: User asks "How do I get a My Number card?"
   - Intake agent stores this in `collected_info["main_request"]`
2. **Follow-up quick-reply**: User clicks "Tokyo (東京)"
   - Intake agent updates `user_location` but keeps `main_request` unchanged
3. **Multi-Step Agent**: Uses `main_request` ("How do I get a My Number card?") instead of latest input ("Tokyo")
   - ✅ Generates correct procedure for **My Number card in Tokyo**

---

## 📊 **Impact**

### Before Fix:
```
User: "How do I get a My Number card?"
Agent: "Which city?"
User: [clicks "Tokyo"]
Agent: ❌ "Here's how to get a Student Visa..." (WRONG!)
```

### After Fix:
```
User: "How do I get a My Number card?"
Agent: "Which city?"
User: [clicks "Tokyo"]
Agent: ✅ "Here's how to get a My Number card in Tokyo..." (CORRECT!)
```

---

## 🔧 **Technical Details**

### Context Preservation Flow:

1. **Initial Question** (`state["user_input"]`):
   - `"How do I get a My Number card?"`
   
2. **Intake Agent** stores in `intake_session`:
   ```python
   collected_info: {
       "main_request": "How do I get a My Number card?",
       "location": None,  # Still missing
       "visa_type": None  # Still missing
   }
   ```

3. **User clicks quick-reply**: `"Tokyo (東京)"`
   - `state["user_input"]` = `"Tokyo (東京)"`
   
4. **Intake Agent updates**:
   ```python
   collected_info: {
       "main_request": "How do I get a My Number card?",  # ✅ Preserved!
       "location": "Tokyo",  # ✅ Updated!
       "visa_type": None
   }
   ```

5. **User clicks another quick-reply**: `"Student (留学)"`
   - `state["user_input"]` = `"Student (留学)"`
   
6. **Intake Agent updates**:
   ```python
   collected_info: {
       "main_request": "How do I get a My Number card?",  # ✅ Still preserved!
       "location": "Tokyo",
       "visa_type": "Student"  # ✅ Updated!
   }
   ```

7. **Multi-Step Agent** uses `main_request`:
   - Query: `"How do I get a My Number card?"`
   - Context: `{location: "Tokyo", visa_type: "Student"}`
   - ✅ **Generates correct procedure for My Number card as a student in Tokyo**

---

## 🧪 **Testing**

### Test Scenario:
```bash
# Start fresh session
1. Ask: "How do I get a my number card?"
2. Agent asks: "Which city are you in?"
3. Click: "Tokyo (東京)"
4. Agent asks: "What type of visa?"
5. Click: "Student (留学)"
6. Agent should respond with: "My Number card application for students in Tokyo"
   ❌ Before fix: "Student Visa and Initial Residency Setup"
   ✅ After fix: "My Number card application procedure"
```

### Expected Logs (After Fix):
```
INFO: QUERY SYNTHESIS - Original: 'How do I get a My Number card?', Latest: 'Student (留学)'
INFO: Synthesized query: 'My Number card application student Tokyo Japan'
INFO: 📋 Using original main_request: 'How do I get a My Number card?' instead of latest input: 'Student (留学)'
INFO: 📋 MULTI-STEP PROCEDURE - Analyzing: 'How do I get a My Number card?'
INFO: ✅ MULTI-STEP PROCEDURE DETECTED: 'My Number Card Application Process'
```

---

## 📝 **Related Files**

### Other Files That Already Use `main_request` Correctly:
1. **`app/nodes/scope_checker.py`** (lines 51-61)
   - Already uses `main_request` for scope checking ✅
   
2. **`app/nodes/hybrid_search.py`** (lines 82-87)
   - Already uses `main_request` to augment queries ✅
   
3. **`app/nodes/vector_rag.py`** (lines 27-33)
   - Already uses `main_request` for vector search ✅

### Fixed File:
4. **`app/nodes/multi_step_procedure_agent.py`** (lines 101-111)
   - **NOW FIXED** ✅

---

## 🎯 **Summary**

**Issue**: Multi-Step Procedure Agent analyzed quick-reply answers instead of original questions.

**Fix**: Use `intake_session.collected_info["main_request"]` instead of `state["user_input"]`.

**Result**: Agent now maintains context correctly across multiple quick-reply interactions!

---

**Status**: ✅ **FIXED**  
**Date**: 2025-10-03  
**Impact**: Critical UX fix for quick-reply feature

