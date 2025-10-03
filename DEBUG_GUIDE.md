# 🐛 Japan Helpdesk - Debugging Guide

This guide provides comprehensive debugging tools and techniques for the Japan Helpdesk system.

## 🚀 Quick Fix Summary

**Problem**: 422 Unprocessable Entity error when sending requests from frontend
**Root Cause**: Pydantic model `session_id: str = None` doesn't accept JSON `null` values
**Solution**: Changed to `session_id: str | None = None` in `app/server.py`

## 🛠️ VSCode Debugging Setup

### **1. Launch Configurations**

Use **Ctrl+Shift+D** (or **Cmd+Shift+D** on Mac) to open the Debug panel, then select:

| Configuration | Purpose | Environment |
|---------------|---------|-------------|
| 🐍 **Debug FastAPI Server** | Debug backend with breakpoints | Langfuse disabled |
| 🔍 **Debug FastAPI Server (with Langfuse)** | Debug with full observability | Langfuse enabled |
| 🧪 **Debug API Test Script** | Test API without frontend | Isolated testing |
| 🤖 **Debug Single LangGraph Node** | Debug individual workflow nodes | Node-level testing |

### **2. Setting Breakpoints**

**Backend Breakpoints (Python):**
```python
# In app/server.py - Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    # Set breakpoint here to inspect incoming requests
    logger.info(f"Received chat request: {request}")  # <- BREAKPOINT
    
# In app/nodes/*.py - Individual nodes
async def adversarial_detector_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    # Set breakpoint here to debug node logic
    start_time = time.time()  # <- BREAKPOINT
```

**Frontend Breakpoints (TypeScript):**
```typescript
// In frontend/src/api.ts
export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  try {
    const response = await api.post<ChatResponse>('/chat', request);  // <- BREAKPOINT
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);  // <- BREAKPOINT
    throw new Error('Failed to send message. Please try again.');
  }
};
```

## 🧪 Debug Scripts

### **1. API Testing Script**
```bash
# Test API directly without frontend
cd /Users/tapatun/adk-samples/japan-helpdesk-deployable
uv run python debug_api.py
```

**What it tests:**
- ✅ Pydantic model validation
- ✅ JSON serialization/deserialization  
- ✅ Agent workflow processing
- ✅ Response model validation

### **2. Individual Node Testing**
```bash
# Test specific LangGraph nodes
uv run python debug_node.py
```

**What it tests:**
- 🛡️ Adversarial detector with various inputs
- 🎯 Scope checker with in/out-of-scope queries
- 🔍 Hybrid search functionality

### **3. Manual API Testing**
```bash
# Test with curl (same data that caused 422 error)
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How do I renew my student visa?","user_id":"test_user","session_id":null}'
```

## 🔍 Common Debugging Scenarios

### **Scenario 1: 422 Unprocessable Entity**

**Symptoms:**
```
INFO: 127.0.0.1:63843 - "POST /chat HTTP/1.1" 422 Unprocessable Entity
```

**Debug Steps:**
1. Check server logs for request body
2. Validate Pydantic models match frontend types
3. Test with `debug_api.py` script
4. Use VSCode debugger on `chat_endpoint`

**Common Causes:**
- Type mismatches (e.g., `str = None` vs `str | None = None`)
- Missing required fields
- Invalid JSON format

### **Scenario 2: LangGraph Node Failures**

**Symptoms:**
```python
state["errors"].append(f"Node XYZ failed: {str(e)}")
```

**Debug Steps:**
1. Run `debug_node.py` to test individual nodes
2. Set breakpoints in specific node functions
3. Check Langfuse traces (if enabled)
4. Validate input/output schemas

### **Scenario 3: Frontend API Errors**

**Symptoms:**
```javascript
API Response Error: Network Error / 500 Internal Server Error
```

**Debug Steps:**
1. Check browser Network tab
2. Verify API base URL in `frontend/src/api.ts`
3. Test backend health: `curl http://localhost:8080/health`
4. Check CORS configuration

### **Scenario 4: Langfuse Integration Issues**

**Symptoms:**
```python
langfuse.exceptions.LangfuseException: API key not found
```

**Debug Steps:**
1. Set `LANGFUSE_ENABLED=false` for testing
2. Check `.env` file configuration
3. Verify Langfuse credentials
4. Use fallback mode for development

## 🔧 Advanced Debugging Techniques

### **1. Request/Response Logging**

The server includes comprehensive logging middleware:

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Request body: {body.decode('utf-8')}")
    # ... response logging
```

### **2. State Inspection**

Add temporary logging to inspect LangGraph state:

```python
async def your_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    # Temporary debug logging
    print(f"🔍 DEBUG - Input state: {state}")
    
    # Your node logic here
    
    print(f"🔍 DEBUG - Output state: {state}")
    return state
```

### **3. Frontend Network Debugging**

Use browser DevTools:
1. **Network Tab**: Inspect request/response data
2. **Console Tab**: Check JavaScript errors
3. **Application Tab**: Inspect localStorage/sessionStorage

### **4. Performance Profiling**

Monitor processing times:

```python
import time

start_time = time.time()
# Your code here
processing_time = time.time() - start_time
logger.info(f"Processing time: {processing_time:.2f}s")
```

## 📊 Health Checks & Monitoring

### **System Health**
```bash
# Backend health
curl http://localhost:8080/health

# Frontend health  
curl http://localhost:3000

# Workflow visualization
curl http://localhost:8080/workflow/visualization
```

### **Log Monitoring**
```bash
# Watch server logs in real-time
tail -f server.log

# Filter for errors
grep -i error server.log

# Filter for specific user sessions
grep "session_abc123" server.log
```

## 🎯 Best Practices

### **1. Debugging Workflow**
1. **Reproduce** the issue consistently
2. **Isolate** the problem (frontend vs backend vs specific node)
3. **Use debug scripts** to test components individually
4. **Set strategic breakpoints** in VSCode
5. **Check logs** for detailed error information
6. **Test fixes** with both debug scripts and full system

### **2. Error Handling**
- Always include comprehensive error logging
- Use try/catch blocks with specific error types
- Provide fallback responses for critical failures
- Log both user-facing and technical error details

### **3. Development Environment**
- Use `LANGFUSE_ENABLED=false` for faster debugging
- Keep debug scripts updated with new features
- Use VSCode's integrated terminal for consistency
- Leverage type hints for better IDE support

## 🚨 Emergency Debugging

If the system is completely broken:

1. **Check basic connectivity:**
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:3000
   ```

2. **Test individual components:**
   ```bash
   uv run python debug_api.py
   uv run python debug_node.py
   ```

3. **Reset to known good state:**
   ```bash
   # Kill all processes
   pkill -f uvicorn
   pkill -f "npm run dev"
   
   # Restart with clean environment
   LANGFUSE_ENABLED=false uv run uvicorn app.server:app --host 0.0.0.0 --port 8080 --reload
   cd frontend && npm run dev
   ```

4. **Check for common issues:**
   - Port conflicts (8080, 3000)
   - Environment variable mismatches
   - Python virtual environment activation
   - Node.js dependency issues

---

**💡 Pro Tip**: Always test your fixes with both the debug scripts AND the full frontend-backend integration to ensure everything works end-to-end!
