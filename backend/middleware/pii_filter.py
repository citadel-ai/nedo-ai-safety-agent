"""
PII filtering middleware for FastAPI.

Automatically detects and optionally masks PII in requests and responses.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from typing import Dict, Any

from ..evaluation.safety import PIIDetector
from ..evaluation.audit import get_audit_logger, AuditEventType, AuditSeverity
from ..evaluation.alerts import get_alert_manager
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class PIIFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect and optionally mask PII in API requests and responses.
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize PII filter middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.pii_detector = PIIDetector()
        self.audit_logger = get_audit_logger()
        self.alert_manager = get_alert_manager()
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and response for PII.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response
        """
        # Only check JSON endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Get thread_id from request if available
        thread_id = "unknown"
        
        try:
            # Check request body for PII
            if request.method in ["POST", "PUT", "PATCH"]:
                # Read body
                body = await request.body()
                
                if body:
                    try:
                        body_json = json.loads(body)
                        thread_id = body_json.get("thread_id", "unknown")
                        
                        # Check for PII in request
                        self._check_request_pii(body_json, thread_id)
                        
                        # Need to make body available again for route handler
                        async def receive():
                            return {"type": "http.request", "body": body}
                        
                        request._receive = receive
                        
                    except json.JSONDecodeError:
                        pass
            
            # Process request
            response = await call_next(request)
            
            # Check response for PII
            if response.status_code == 200 and hasattr(response, 'body'):
                await self._check_response_pii(response, thread_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in PII filter middleware: {e}")
            return await call_next(request)
    
    def _check_request_pii(self, body: Dict[str, Any], thread_id: str):
        """
        Check request for PII.
        
        Args:
            body: Request body
            thread_id: Thread identifier
        """
        # Check question/query fields
        text_to_check = ""
        if "question" in body:
            text_to_check = body["question"]
        elif "query" in body:
            text_to_check = body["query"]
        
        if not text_to_check:
            return
        
        # Run PII detection
        result = self.pii_detector.detect_pii(text_to_check)
        
        if result.has_pii:
            # Log to audit
            self.audit_logger.log_pii_detection(
                thread_id=thread_id,
                pii_types=result.pii_types,
                risk_level=result.risk_level,
                location="request"
            )
            
            # Alert if high risk
            if result.risk_level in ['medium', 'high']:
                self.alert_manager.alert_pii_detected(
                    pii_types=result.pii_types,
                    risk_level=result.risk_level,
                    location="request",
                    thread_id=thread_id
                )
    
    async def _check_response_pii(self, response: Response, thread_id: str):
        """
        Check response for PII.
        
        Args:
            response: FastAPI response
            thread_id: Thread identifier
        """
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Try to parse as JSON
            try:
                body_json = json.loads(body)
                
                # Check answer field
                if "answer" in body_json:
                    result = self.pii_detector.detect_pii(body_json["answer"])
                    
                    if result.has_pii:
                        # Log to audit
                        self.audit_logger.log_pii_detection(
                            thread_id=thread_id,
                            pii_types=result.pii_types,
                            risk_level=result.risk_level,
                            location="response"
                        )
                        
                        # Alert if high risk
                        if result.risk_level in ['medium', 'high']:
                            self.alert_manager.alert_pii_detected(
                                pii_types=result.pii_types,
                                risk_level=result.risk_level,
                                location="response",
                                thread_id=thread_id
                            )
                        
                        # Mask if configured
                        if self.pii_detector.masking_mode == 'mask_output':
                            body_json["answer"] = self.pii_detector.mask_pii(
                                body_json["answer"],
                                result
                            )
                            body_json["pii_masked"] = True
                            body = json.dumps(body_json).encode()
                
            except json.JSONDecodeError:
                pass
            
            # Recreate response with potentially masked body
            response.body_iterator = iter([body])
            
        except Exception as e:
            logger.error(f"Error checking response PII: {e}")

