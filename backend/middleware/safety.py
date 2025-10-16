"""
Safety middleware for FastAPI.

Performs safety checks on responses before they are returned to users.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from typing import Dict, Any

from ..evaluation.safety import ContentSafetyChecker
from ..evaluation.audit import get_audit_logger, AuditEventType, AuditSeverity
from ..evaluation.alerts import get_alert_manager
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class SafetyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to perform safety checks on API responses.
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize safety middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.safety_checker = ContentSafetyChecker()
        self.audit_logger = get_audit_logger()
        self.alert_manager = get_alert_manager()
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and check response safety.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response
        """
        # Only check query endpoints
        if request.url.path != "/api/query":
            return await call_next(request)
        
        thread_id = "unknown"
        
        try:
            # Get thread_id if available
            if request.method == "POST":
                body = await request.body()
                if body:
                    try:
                        body_json = json.loads(body)
                        thread_id = body_json.get("thread_id", "unknown")
                        
                        # Make body available again
                        async def receive():
                            return {"type": "http.request", "body": body}
                        request._receive = receive
                    except:
                        pass
            
            # Process request
            response = await call_next(request)
            
            # Check response safety
            if response.status_code == 200:
                await self._check_response_safety(response, thread_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in safety middleware: {e}")
            return await call_next(request)
    
    async def _check_response_safety(self, response: Response, thread_id: str):
        """
        Check response for safety issues.
        
        Args:
            response: FastAPI response
            thread_id: Thread identifier
        """
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Parse JSON
            try:
                body_json = json.loads(body)
                
                # Check answer field
                if "answer" in body_json:
                    answer = body_json["answer"]
                    citations = body_json.get("citations", [])
                    
                    # Run safety check
                    safety_result = self.safety_checker.check_safety(
                        text=answer,
                        citations=citations
                    )
                    
                    # Log safety metrics
                    if not safety_result.is_safe:
                        logger.warning(
                            f"Unsafe response detected for thread {thread_id}: "
                            f"score={safety_result.safety_score:.2f}, "
                            f"issues={safety_result.issues}"
                        )
                        
                        # Log to audit
                        self.audit_logger.log_safety_violation(
                            thread_id=thread_id,
                            violation_type="content_safety",
                            details={
                                "safety_score": safety_result.safety_score,
                                "toxicity_score": safety_result.toxicity_score,
                                "citation_coverage": safety_result.citation_coverage,
                                "issues": safety_result.issues
                            }
                        )
                        
                        # Create alert
                        self.alert_manager.alert_safety_violation(
                            violation_type="content_safety",
                            details=safety_result.to_dict(),
                            thread_id=thread_id
                        )
                    
                    # Add safety metadata to response
                    body_json["_safety"] = {
                        "checked": True,
                        "score": safety_result.safety_score,
                        "is_safe": safety_result.is_safe
                    }
                    
                    body = json.dumps(body_json).encode()
                
            except json.JSONDecodeError:
                pass
            
            # Recreate response with safety metadata
            response.body_iterator = iter([body])
            
        except Exception as e:
            logger.error(f"Error checking response safety: {e}")

