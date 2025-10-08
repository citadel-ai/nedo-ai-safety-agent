import logging
import os
import uuid
from typing import Any

import uvicorn

# Load environment variables from .env file
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel

from app.agent import JapanHelpdeskAgent
from app.mock_agent import MockJapanHelpdeskAgent
from app.real_google_search import get_search_config
from app.real_vector_db import get_vector_db
from app.utils.observability import (
    get_langfuse_client,
    is_langfuse_enabled,
    score_langfuse_trace,
)

load_dotenv()

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agent based on configuration
AGENT_IMPLEMENTATION = os.getenv("AGENT_IMPLEMENTATION", "production")  # production | mock
try:
    if AGENT_IMPLEMENTATION == "mock":
        agent = MockJapanHelpdeskAgent()
        AGENT_TYPE = "mock"
        logger.info("Initialized mock agent")
    else:
        agent = JapanHelpdeskAgent()
        AGENT_TYPE = "production"
        logger.info("Initialized production agent")
except Exception as e:
    logger.warning(f"Failed to initialize selected agent '{AGENT_IMPLEMENTATION}': {e}")
    logger.info("Falling back to mock agent")
    agent = MockJapanHelpdeskAgent()
    AGENT_TYPE = "mock"

# Initialize FastAPI app and logging
app = FastAPI(
    title="Japan Helpdesk - LangGraph + Langfuse",
    description="AI-powered helpdesk for foreigners in Japan with comprehensive observability and guardrails",
    version="1.0.0",
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Cloud logging if available (optional for development)
try:
    if (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        and os.getenv("GOOGLE_CLOUD_PROJECT") != "test"
    ):
        logging_client = google_cloud_logging.Client()
        logging_client.setup_logging()
        logger.info("Google Cloud logging initialized")
    else:
        logger.info("Google Cloud logging skipped (no valid project configured)")
except Exception as e:
    logger.warning(f"Google Cloud logging not available: {e}")

# Get Langfuse client from observability utility
langfuse = get_langfuse_client()
if is_langfuse_enabled():
    logger.info("🔍 Langfuse v3 observability: ENABLED")
else:
    logger.info("🔍 Langfuse observability: DISABLED (running in fallback mode)")


# Add request logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")

    # For POST requests, try to log the body
    if request.method == "POST":
        try:
            body = await request.body()
            logger.info(f"Request body: {body.decode('utf-8')}")
            # Re-create request with body for FastAPI to process

            # Create a new request with the body
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive
        except Exception as e:
            logger.error(f"Error reading request body: {e}")

    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    confidence_score: float
    sources: list[str]
    recommendations: list[str]
    session_id: str
    completed_steps: list[str]
    errors: list[str]
    processing_time: float
    tokens_used: int
    metadata: dict[str, Any]
    suggested_answers: list[str] = []  # Quick-reply suggestions from intake agent


class HealthResponse(BaseModel):
    status: str
    version: str
    workflow_type: str


# Routes
# Mount static files for production frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    # Mount the assets directory at /assets (for JS, CSS files)
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Mount the entire static directory at /static for other files
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_frontend():
        """Serve the React frontend in production."""
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return RedirectResponse(url="/docs")
else:

    @app.get("/", response_class=RedirectResponse)
    def redirect_root_to_docs() -> RedirectResponse:
        """Redirect the root URL to the API documentation (development mode)."""
        return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Comprehensive health check endpoint with diagnostics."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        workflow_type=f"langgraph-{AGENT_TYPE}",
    )


@app.get("/system-info")
def system_info_endpoint() -> dict[str, Any]:
    """Get detailed system configuration information."""
    try:
        # Get vector database info
        vector_info = {}
        try:
            vector_db = get_vector_db()
            vector_info = vector_db.get_collection_info()
        except Exception as e:
            vector_info = {"error": f"Vector DB not available: {e}"}

        # Get search configuration
        search_info = {}
        try:
            search_info = get_search_config()
        except Exception as e:
            search_info = {"error": f"Search config not available: {e}"}

        return {
            "status": "success",
            "agent_type": f"langgraph-{AGENT_TYPE}",
            "vector_database": vector_info,
            "google_search": search_info,
            "features": {
                "real_vector_search": "error" not in vector_info,
                "real_google_search": "error" not in search_info,
                "langfuse_observability": os.getenv("LANGFUSE_ENABLED", "false").lower()
                == "true",
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "fallback": "Using basic system information",
        }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint for Japan Helpdesk with full observability.

    Args:
        request: Chat request with message and user info

    Returns:
        Comprehensive chat response with observability data
    """
    try:
        # Log the incoming request for debugging
        logger.info(f"Received chat request: {request}")
        logger.info(
            f"Request data - message: '{request.message}', user_id: '{request.user_id}', session_id: {request.session_id}"
        )

        # Generate session ID if not provided
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"

        # Log request processing
        logger.info(
            f"Processing chat request from user {request.user_id}, session {session_id}"
        )

        # Process query through LangGraph workflow
        result = await agent.process_query(
            user_input=request.message,
            user_id=request.user_id,
            session_id=session_id,
        )

        # Log response
        logger.info(
            f"Chat response generated for session {session_id}, confidence: {result['confidence_score']}"
        )
        logger.info(
            f"Response text: {result.get('response', 'N/A')[:200]}..."
        )  # Log first 200 chars
        logger.info(f"Response length: {len(result.get('response', ''))} characters")

        # Create response object
        response = ChatResponse(**result)
        logger.info("Response object created successfully")
        logger.info(
            f"ChatResponse.response: {response.response[:200] if response.response else 'None'}..."
        )

        return response

    except Exception as e:
        logger.error(f"Chat endpoint error: {e!s}")
        logger.error(f"Error type: {type(e)}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e!s}"
        ) from e


@app.get("/workflow/visualization")
def get_workflow_visualization() -> dict[str, str]:
    """Get workflow visualization for debugging (ASCII)."""

    def _draw_ascii() -> str:
        try:
            # Preferred: compiled app's graph
            if hasattr(agent, "agent") and hasattr(agent.agent, "get_graph"):
                return agent.agent.get_graph().draw_ascii()
            # Some versions expose graph on compiled app directly
            if hasattr(agent, "agent") and hasattr(agent.agent, "draw_ascii"):
                return agent.agent.draw_ascii()  # type: ignore[attr-defined]
            # Fallback: compile a temporary app and draw
            if hasattr(agent, "workflow") and hasattr(agent.workflow, "compile"):
                temp_app = agent.workflow.compile()  # type: ignore[attr-defined]
                if hasattr(temp_app, "get_graph"):
                    return temp_app.get_graph().draw_ascii()
                if hasattr(temp_app, "draw_ascii"):
                    return temp_app.draw_ascii()  # type: ignore[attr-defined]
        except Exception as e:
            return f"Workflow visualization unavailable: {e}"
        return "Workflow visualization unavailable: unsupported LangGraph version"

    return {
        "workflow": _draw_ascii(),
        "description": """
Japan Helpdesk LangGraph Workflow:

1. adversarial_detector → [intake_agent | END (BLOCKED)]
2. intake_agent → [intake_agent (loop ≤3) | scope_checker]
3. scope_checker → [vector_rag | hybrid_search | END (OUT_OF_SCOPE)]
4. vector_rag/hybrid_search → [rag_agent | legal_checker]
5. legal_checker → [response_synthesizer | rag_agent (≤2 revisions)]
6. response_synthesizer → END

Guardrails:
- Adversarial inputs: HARD STOP
- Out-of-scope: Terminated
- High-risk categories: Enhanced search
- Legal advice: Auto-revision
- Loop limits: Prevent infinite loops
""",
    }


@app.get("/workflow")
def get_workflow_default() -> dict[str, str]:
    """Compatibility endpoint for frontend: returns the same visualization payload."""
    try:
        # Reuse the same drawing logic as visualization endpoint
        if hasattr(agent, "agent") and hasattr(agent.agent, "get_graph"):
            ascii_graph = agent.agent.get_graph().draw_ascii()
        elif hasattr(agent, "agent") and hasattr(agent.agent, "draw_ascii"):
            ascii_graph = agent.agent.draw_ascii()  # type: ignore[attr-defined]
        elif hasattr(agent, "workflow") and hasattr(agent.workflow, "compile"):
            temp_app = agent.workflow.compile()  # type: ignore[attr-defined]
            ascii_graph = (
                temp_app.get_graph().draw_ascii()
                if hasattr(temp_app, "get_graph")
                else (temp_app.draw_ascii() if hasattr(temp_app, "draw_ascii") else "")
            )
        else:
            ascii_graph = ""
        return {"workflow": ascii_graph, "type": f"langgraph-{AGENT_TYPE}"}
    except Exception as e:
        return {
            "workflow": f"Workflow visualization unavailable: {e}",
            "type": f"langgraph-{AGENT_TYPE}",
        }


@app.post("/feedback")
def collect_feedback(feedback: dict[str, Any]) -> dict[str, str]:
    """Collect user feedback for continuous improvement.

    Args:
        feedback: Feedback data including rating, comments, session_id

    Returns:
        Success confirmation
    """
    try:
        # Log feedback with structured data
        logger.info(f"User feedback received: {feedback}")

        # Send to Langfuse if available
        if is_langfuse_enabled():
            score_langfuse_trace(
                trace_id=feedback.get("trace_id"),
                name="user_feedback",
                value=feedback.get("rating", 0),
                comment=feedback.get("comment", ""),
            )

        return {"status": "success", "message": "Feedback recorded"}

    except Exception as e:
        logger.error(f"Feedback collection error: {e!s}")
        return {"status": "error", "message": "Failed to record feedback"}


# Main execution
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
