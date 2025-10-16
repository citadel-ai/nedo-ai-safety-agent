"""
Metrics middleware for FastAPI.

Automatically tracks latency, cost, and performance metrics for all requests.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from typing import Optional

from ..evaluation.metrics import get_metrics_collector, PerformanceTracker
from ..evaluation.alerts import get_alert_manager
from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track performance metrics for API requests.
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize metrics middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        self.enabled = Config.METRICS_ENABLED
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and track metrics.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response
        """
        if not self.enabled:
            return await call_next(request)
        
        # Only track API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Skip health check
        if request.url.path == "/api/health":
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        thread_id = "unknown"
        success = True
        error_type = None
        
        try:
            # Try to extract thread_id from request
            if request.method in ["POST", "PUT", "PATCH"]:
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
            
            # Check if response indicates error
            if response.status_code >= 400:
                success = False
                if response.status_code == 404:
                    error_type = "not_found"
                elif response.status_code >= 500:
                    error_type = "server_error"
                else:
                    error_type = "client_error"
            
            return response
            
        except Exception as e:
            success = False
            error_type = type(e).__name__
            logger.error(f"Request failed: {e}")
            raise
            
        finally:
            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            # Record metrics
            try:
                self.metrics_collector.record_query(
                    thread_id=thread_id,
                    latency_ms=latency_ms,
                    success=success,
                    error_type=error_type
                )
                
                # Check thresholds and create alerts if needed
                if latency_ms > Config.LATENCY_ALERT_THRESHOLD_MS:
                    self.alert_manager.check_latency(latency_ms, thread_id)
                
            except Exception as e:
                logger.error(f"Failed to record metrics: {e}")
            
            # Log slow requests
            if latency_ms > 1000:  # Log if > 1 second
                logger.info(
                    f"Request {request.url.path}: {latency_ms:.0f}ms "
                    f"(thread: {thread_id}, success: {success})"
                )

