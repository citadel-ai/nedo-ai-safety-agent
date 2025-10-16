"""
FastAPI server for the Japan Procedures Agent.

Provides REST API endpoints for querying the agent and serving the frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional

from ..services.context import set_user_context
from ..services.query import query_agent, get_thread_state
from ..utils.config import Config
from ..utils.logging_config import setup_logging
from ..utils.langfuse_config import initialize_langfuse, flush_langfuse
from ..evaluation.benchmarks import get_benchmark_manager
from ..evaluation.metrics import get_metrics_collector
from ..evaluation.alerts import get_alert_manager
from ..evaluation.audit import get_audit_logger
from ..middleware.pii_filter import PIIFilterMiddleware
from ..middleware.metrics import MetricsMiddleware
from ..middleware.safety import SafetyMiddleware

# Setup logging
setup_logging()

# Initialize Langfuse tracing (v3)
initialize_langfuse()

# Get the dist directory path (React build output)
DIST_DIR = Path(__file__).parent.parent.parent / "agent" / "dist"

# Initialize FastAPI app
app = FastAPI(
    title="Japan Procedures Agent",
    description="AI-powered assistant for Japanese official procedures",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add evaluation middleware
app.add_middleware(SafetyMiddleware)
app.add_middleware(PIIFilterMiddleware)
app.add_middleware(MetricsMiddleware)


# Add shutdown event to flush Langfuse traces
@app.on_event("shutdown")
async def shutdown_event():
    """Flush Langfuse traces before shutdown."""
    flush_langfuse()


# Request/Response models
class UserContextRequest(BaseModel):
    thread_id: str
    visa_type: str
    location: str
    conversation_mode: str = "multi"  # 'single' or 'multi'


class QueryRequest(BaseModel):
    question: str
    thread_id: str
    conversation_mode: str | None = None  # Optional: allows switching mid-conversation


class Citation(BaseModel):
    citation_number: int
    title: str | None = None
    url: str | None = None
    gs_uri: str | None = None
    pages: list[int] = []
    source_type: str | None = None


class UsefulPhrase(BaseModel):
    japanese: str
    romaji: str
    english: str


class UsefulPlace(BaseModel):
    name: str
    address: str
    place_id: str | None = None
    maps_url: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation] = []  # Changed from list[str] to list[Citation]
    error: str | None = None
    collected_facts: list[str] = []
    useful_phrases: list[UsefulPhrase] = []
    useful_places: list[UsefulPlace] = []


@app.get("/")
async def root():
    """Serve the React frontend."""
    index_file = DIST_DIR / "index.html"
    
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "Japan Procedures Agent API",
        "docs": "/docs",
        "note": "Frontend not built yet. Run: cd frontend && npm run build"
    }


@app.post("/api/context")
async def set_context(request: UserContextRequest):
    """
    Set user context (visa type, location, and conversation mode) for a thread.
    
    This initializes the LangGraph checkpoint with user context.
    Must be called before /api/query for a new thread.
    
    All state is managed via LangGraph checkpointing - no duplicate storage.
    """
    try:
        result = set_user_context(
            thread_id=request.thread_id,
            visa_type=request.visa_type,
            location=request.location,
            conversation_mode=request.conversation_mode
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the agent with a question.
    
    Uses LangGraph checkpointing for state persistence.
    State is automatically loaded and saved via thread_id.
    No manual session management needed.
    
    Args:
        request: QueryRequest with question, thread_id, and optional conversation_mode
        
    Returns:
        QueryResponse with answer, citations, collected facts
    """
    try:
        result = query_agent(
            question=request.question,
            thread_id=request.thread_id,
            conversation_mode=request.conversation_mode
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/thread/{thread_id}")
async def get_thread(thread_id: str):
    """
    Get current state of a conversation thread.
    
    Useful for debugging or displaying thread info.
    All state comes from LangGraph checkpointing.
    """
    try:
        return get_thread_state(thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RemoveFactRequest(BaseModel):
    fact_key: str


@app.delete("/api/thread/{thread_id}/facts")
async def remove_fact(thread_id: str, request: RemoveFactRequest):
    """
    Remove a specific fact from collected_facts.
    
    Args:
        thread_id: Thread identifier
        request: RemoveFactRequest with fact_key to remove
    
    Returns:
        Updated collected_facts dict
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"DELETE request for thread {thread_id}, fact_key: {request.fact_key}")
    
    try:
        from backend.services.query import remove_collected_fact
        result = remove_collected_fact(thread_id, request.fact_key)
        logger.info(f"Remove fact result: {result}")
        if "error" in result:
            logger.warning(f"Error in remove_fact: {result['error']}")
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception in remove_fact: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feedback API ====================

class FeedbackRatingRequest(BaseModel):
    thread_id: str
    query: str
    rating: int  # 1-5 stars
    comment: Optional[str] = None


class FeedbackFlagRequest(BaseModel):
    thread_id: str
    query: str
    reason: str
    details: Optional[str] = None


@app.post("/api/feedback/rating")
async def submit_rating(request: FeedbackRatingRequest):
    """
    Submit user rating for a response.
    
    Args:
        request: FeedbackRatingRequest with rating (1-5)
        
    Returns:
        Success confirmation
    """
    try:
        # Validate rating
        if not (1 <= request.rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Log to audit
        audit_logger = get_audit_logger()
        audit_logger.log_user_action(
            thread_id=request.thread_id,
            action_type="feedback",
            details={
                "rating": request.rating,
                "comment": request.comment,
                "query": request.query[:100]
            }
        )
        
        return {
            "status": "success",
            "message": "Feedback recorded",
            "rating": request.rating
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback/flag")
async def flag_response(request: FeedbackFlagRequest):
    """
    Flag a response as incorrect or problematic.
    
    Args:
        request: FeedbackFlagRequest with reason
        
    Returns:
        Success confirmation
    """
    try:
        # Log to audit
        audit_logger = get_audit_logger()
        audit_logger.log_user_action(
            thread_id=request.thread_id,
            action_type="flag_response",
            details={
                "reason": request.reason,
                "details": request.details,
                "query": request.query[:100]
            }
        )
        
        return {
            "status": "success",
            "message": "Response flagged for review"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Metrics API ====================

@app.get("/api/metrics/realtime")
async def get_realtime_metrics():
    """
    Get real-time metrics snapshot.
    
    Returns:
        Current system metrics
    """
    try:
        metrics_collector = get_metrics_collector()
        return metrics_collector.get_realtime_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/nodes")
async def get_node_metrics():
    """
    Get per-node performance metrics.
    
    Returns:
        Node-level latency statistics
    """
    try:
        metrics_collector = get_metrics_collector()
        return metrics_collector.get_node_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Alerts API ====================

@app.get("/api/alerts/active")
async def get_active_alerts(
    unacknowledged_only: bool = False,
    severity: Optional[str] = None
):
    """
    Get active alerts.
    
    Args:
        unacknowledged_only: Only return unacknowledged alerts
        severity: Filter by severity level
        
    Returns:
        List of active alerts
    """
    try:
        alert_manager = get_alert_manager()
        
        # Parse severity if provided
        from ..evaluation.alerts import AlertSeverity
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity: {severity}"
                )
        
        alerts = alert_manager.get_active_alerts(
            severity=severity_enum,
            unacknowledged_only=unacknowledged_only
        )
        
        return {
            "count": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts/summary")
async def get_alerts_summary():
    """
    Get alert summary statistics.
    
    Returns:
        Alert statistics
    """
    try:
        alert_manager = get_alert_manager()
        return alert_manager.get_alert_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Benchmarks API ====================

class BenchmarkCreateRequest(BaseModel):
    query: str
    context: dict
    expected_answer_elements: List[str]
    category: str
    created_by: str
    must_include_citations: bool = True
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


@app.post("/api/benchmarks/create")
async def create_benchmark(request: BenchmarkCreateRequest):
    """
    Create a new benchmark (SME function).
    
    Args:
        request: BenchmarkCreateRequest
        
    Returns:
        Created benchmark
    """
    try:
        benchmark_manager = get_benchmark_manager()
        
        benchmark = benchmark_manager.create_benchmark(
            query=request.query,
            context=request.context,
            expected_answer_elements=request.expected_answer_elements,
            category=request.category,
            created_by=request.created_by,
            must_include_citations=request.must_include_citations,
            tags=request.tags,
            notes=request.notes
        )
        
        return benchmark.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmarks/list")
async def list_benchmarks(
    category: Optional[str] = None,
    tags: Optional[str] = None  # Comma-separated
):
    """
    List benchmarks with optional filters.
    
    Args:
        category: Filter by category
        tags: Filter by tags (comma-separated)
        
    Returns:
        List of benchmarks
    """
    try:
        benchmark_manager = get_benchmark_manager()
        
        # Parse tags
        tags_list = tags.split(",") if tags else None
        
        benchmarks = benchmark_manager.list_benchmarks(
            category=category,
            tags=tags_list
        )
        
        return {
            "count": len(benchmarks),
            "benchmarks": [b.to_dict() for b in benchmarks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmarks/results")
async def get_benchmark_results(limit: int = 10):
    """
    Get historical benchmark results.
    
    Args:
        limit: Number of runs to return
        
    Returns:
        Benchmark run history
    """
    try:
        benchmark_manager = get_benchmark_manager()
        results = benchmark_manager.get_results_history(limit=limit)
        
        return {
            "count": len(results),
            "runs": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "japan_procedures_agent"}


# Mount React build assets if they exist
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.server:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )

