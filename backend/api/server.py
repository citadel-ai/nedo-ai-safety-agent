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

from ..services.context import set_user_context
from ..services.query import query_agent, get_thread_state, submit_feedback
from ..utils.config import Config
from ..utils.logging_config import setup_logging
from ..utils.langfuse_config import initialize_langfuse, flush_langfuse

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
    collected_facts: dict[str, str] = {}
    useful_phrases: list[UsefulPhrase] = []
    useful_places: list[UsefulPlace] = []
    trace_id: str | None = None  # For user feedback tracking via Langfuse




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
            conversation_mode=request.conversation_mode,
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
            conversation_mode=request.conversation_mode,
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


class FeedbackRequest(BaseModel):
    trace_id: str
    value: int  # 1 = thumbs up, 0 = thumbs down
    comment: str | None = None


class FeedbackResponse(BaseModel):
    status: str
    trace_id: str | None = None
    value: int | None = None
    message: str | None = None


@app.post("/api/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest):
    """
    Submit user feedback (thumbs up/down) for a response.

    This logs the feedback as a score to Langfuse, allowing filtering
    and analysis of user-rated responses for evaluation and testing.

    Args:
        request: FeedbackRequest with trace_id, value (1=positive, 0=negative), and optional comment

    Returns:
        FeedbackResponse with status
    """
    try:
        # Validate value
        if request.value not in (0, 1):
            raise HTTPException(
                status_code=400,
                detail="Value must be 0 (thumbs down) or 1 (thumbs up)",
            )

        result = submit_feedback(
            trace_id=request.trace_id,
            value=request.value,
            comment=request.comment,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        return FeedbackResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "japan_procedures_agent"}


# Mount React build assets and static files if they exist
if DIST_DIR.exists():
    # Mount assets directory
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")
    # Serve static files from root (favicon, images, etc.)
    # This needs to be last to avoid overriding API routes
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.server:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True,
    )
