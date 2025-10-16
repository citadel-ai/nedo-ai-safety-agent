"""
Enhanced audit logging for compliance and governance.

Provides comprehensive audit trails for all agent actions, decisions,
and safety events.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path
from enum import Enum

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Agent lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    QUERY_RECEIVED = "query_received"
    RESPONSE_GENERATED = "response_generated"
    
    # Safety events
    SAFETY_VIOLATION = "safety_violation"
    PII_DETECTED = "pii_detected"
    CONTENT_FILTERED = "content_filtered"
    
    # Quality events
    LOW_QUALITY_RESPONSE = "low_quality_response"
    BENCHMARK_FAILED = "benchmark_failed"
    
    # User actions
    USER_FEEDBACK = "user_feedback"
    FACT_DELETED = "fact_deleted"
    CONTEXT_CHANGED = "context_changed"
    
    # LLM decisions
    SCOPE_CHECK = "scope_check"
    FACT_EXTRACTION = "fact_extraction"
    TOOL_INVOCATION = "tool_invocation"
    
    # System events
    ERROR = "error"
    ALERT_TRIGGERED = "alert_triggered"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """
    Audit logger for compliance and governance.
    
    Logs all significant events to both:
    1. Dedicated audit.log file
    2. Langfuse (if enabled) with special 'audit' tag
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create dedicated audit log file
        self.audit_log_path = self.log_dir / "audit.log"
        
        # Set up file handler for audit log
        self.file_handler = logging.FileHandler(self.audit_log_path)
        self.file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        self.file_handler.setFormatter(formatter)
        
        # Add handler to logger
        audit_file_logger = logging.getLogger("audit")
        audit_file_logger.addHandler(self.file_handler)
        audit_file_logger.setLevel(logging.INFO)
        
        logger.info(f"Audit logger initialized: {self.audit_log_path}")
    
    def log_event(
        self,
        event_type: AuditEventType,
        thread_id: str,
        details: Dict[str, Any],
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            thread_id: Thread/session identifier
            details: Event details (will be JSON serialized)
            severity: Event severity
            user_id: Optional user identifier
        """
        # Create audit record
        audit_record = {
            "event_type": event_type.value,
            "thread_id": thread_id,
            "user_id": user_id,
            "severity": severity.value,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        
        # Log to file
        audit_logger = logging.getLogger("audit")
        log_message = json.dumps(audit_record)
        
        if severity == AuditSeverity.CRITICAL:
            audit_logger.critical(log_message)
        elif severity == AuditSeverity.ERROR:
            audit_logger.error(log_message)
        elif severity == AuditSeverity.WARNING:
            audit_logger.warning(log_message)
        else:
            audit_logger.info(log_message)
        
        # Log to Langfuse if enabled
        self._log_to_langfuse(audit_record)
        
        # Log summary to main logger
        logger.info(
            f"AUDIT: {event_type.value} | thread={thread_id} | severity={severity.value}"
        )
    
    def _log_to_langfuse(self, audit_record: Dict[str, Any]):
        """
        Log audit event to Langfuse.
        
        Args:
            audit_record: Audit record to log
        """
        try:
            from ..utils.langfuse_config import get_langfuse_client
            
            client = get_langfuse_client()
            if not client:
                return
            
            # Create Langfuse event
            client.event(
                name=audit_record["event_type"],
                metadata={
                    "audit": True,
                    "severity": audit_record["severity"],
                    "thread_id": audit_record["thread_id"],
                    "user_id": audit_record.get("user_id"),
                    **audit_record["details"]
                },
                session_id=audit_record["thread_id"],
                level=audit_record["severity"]
            )
            
        except Exception as e:
            logger.warning(f"Failed to log audit event to Langfuse: {e}")
    
    def log_session_start(self, thread_id: str, context: Dict[str, Any]):
        """
        Log session start event.
        
        Args:
            thread_id: Thread identifier
            context: Session context (visa type, location, etc.)
        """
        self.log_event(
            event_type=AuditEventType.SESSION_START,
            thread_id=thread_id,
            details={
                "action": "session_started",
                "context": context
            },
            severity=AuditSeverity.INFO
        )
    
    def log_session_end(self, thread_id: str, stats: Dict[str, Any]):
        """
        Log session end event.
        
        Args:
            thread_id: Thread identifier
            stats: Session statistics
        """
        self.log_event(
            event_type=AuditEventType.SESSION_END,
            thread_id=thread_id,
            details={
                "action": "session_ended",
                "stats": stats
            },
            severity=AuditSeverity.INFO
        )
    
    def log_query(
        self,
        thread_id: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log user query.
        
        Args:
            thread_id: Thread identifier
            query: User query text
            metadata: Additional metadata
        """
        self.log_event(
            event_type=AuditEventType.QUERY_RECEIVED,
            thread_id=thread_id,
            details={
                "query": query[:200],  # Truncate long queries
                "query_length": len(query),
                "metadata": metadata or {}
            },
            severity=AuditSeverity.INFO
        )
    
    def log_response(
        self,
        thread_id: str,
        response: str,
        citations_count: int,
        quality_score: Optional[float] = None
    ):
        """
        Log agent response.
        
        Args:
            thread_id: Thread identifier
            response: Agent response text
            citations_count: Number of citations
            quality_score: Optional quality score
        """
        self.log_event(
            event_type=AuditEventType.RESPONSE_GENERATED,
            thread_id=thread_id,
            details={
                "response_length": len(response),
                "word_count": len(response.split()),
                "citations_count": citations_count,
                "quality_score": quality_score
            },
            severity=AuditSeverity.INFO
        )
    
    def log_safety_violation(
        self,
        thread_id: str,
        violation_type: str,
        details: Dict[str, Any]
    ):
        """
        Log safety violation.
        
        Args:
            thread_id: Thread identifier
            violation_type: Type of violation
            details: Violation details
        """
        self.log_event(
            event_type=AuditEventType.SAFETY_VIOLATION,
            thread_id=thread_id,
            details={
                "violation_type": violation_type,
                **details
            },
            severity=AuditSeverity.WARNING
        )
    
    def log_pii_detection(
        self,
        thread_id: str,
        pii_types: list,
        risk_level: str,
        location: str  # 'query' or 'response'
    ):
        """
        Log PII detection event.
        
        Args:
            thread_id: Thread identifier
            pii_types: List of detected PII types
            risk_level: Risk level (low/medium/high)
            location: Where PII was detected
        """
        self.log_event(
            event_type=AuditEventType.PII_DETECTED,
            thread_id=thread_id,
            details={
                "pii_types": pii_types,
                "risk_level": risk_level,
                "location": location
            },
            severity=AuditSeverity.WARNING if risk_level == "high" else AuditSeverity.INFO
        )
    
    def log_tool_invocation(
        self,
        thread_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        success: bool,
        duration_ms: Optional[float] = None
    ):
        """
        Log tool invocation.
        
        Args:
            thread_id: Thread identifier
            tool_name: Name of tool invoked
            parameters: Tool parameters (sanitized)
            success: Whether invocation succeeded
            duration_ms: Execution duration
        """
        self.log_event(
            event_type=AuditEventType.TOOL_INVOCATION,
            thread_id=thread_id,
            details={
                "tool_name": tool_name,
                "parameters": parameters,
                "success": success,
                "duration_ms": duration_ms
            },
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING
        )
    
    def log_llm_decision(
        self,
        thread_id: str,
        decision_type: str,
        decision: str,
        reasoning: Optional[str] = None
    ):
        """
        Log LLM decision.
        
        Args:
            thread_id: Thread identifier
            decision_type: Type of decision (e.g., 'scope_check')
            decision: The decision made
            reasoning: Optional reasoning
        """
        self.log_event(
            event_type=AuditEventType.SCOPE_CHECK,  # Generic for now
            thread_id=thread_id,
            details={
                "decision_type": decision_type,
                "decision": decision,
                "reasoning": reasoning
            },
            severity=AuditSeverity.INFO
        )
    
    def log_user_action(
        self,
        thread_id: str,
        action_type: str,
        details: Dict[str, Any]
    ):
        """
        Log user action.
        
        Args:
            thread_id: Thread identifier
            action_type: Type of action
            details: Action details
        """
        # Map action type to event type
        event_type_map = {
            "feedback": AuditEventType.USER_FEEDBACK,
            "fact_deleted": AuditEventType.FACT_DELETED,
            "context_changed": AuditEventType.CONTEXT_CHANGED
        }
        
        event_type = event_type_map.get(action_type, AuditEventType.USER_FEEDBACK)
        
        self.log_event(
            event_type=event_type,
            thread_id=thread_id,
            details={
                "action_type": action_type,
                **details
            },
            severity=AuditSeverity.INFO
        )
    
    def log_error(
        self,
        thread_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ):
        """
        Log error event.
        
        Args:
            thread_id: Thread identifier
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
        """
        self.log_event(
            event_type=AuditEventType.ERROR,
            thread_id=thread_id,
            details={
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace
            },
            severity=AuditSeverity.ERROR
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_audit_event(
    event_type: AuditEventType,
    thread_id: str,
    details: Dict[str, Any],
    severity: AuditSeverity = AuditSeverity.INFO,
    user_id: Optional[str] = None
):
    """
    Convenience function to log audit event.
    
    Args:
        event_type: Type of event
        thread_id: Thread/session identifier
        details: Event details
        severity: Event severity
        user_id: Optional user identifier
    """
    audit_logger = get_audit_logger()
    audit_logger.log_event(event_type, thread_id, details, severity, user_id)

