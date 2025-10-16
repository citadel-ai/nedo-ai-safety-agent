"""
Real-time alerting system for safety and performance issues.

Monitors metrics and triggers alerts when thresholds are exceeded.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    HIGH_LATENCY = "high_latency"
    HIGH_COST = "high_cost"
    HIGH_ERROR_RATE = "high_error_rate"
    SAFETY_VIOLATION = "safety_violation"
    PII_DETECTED = "pii_detected"
    LOW_QUALITY = "low_quality"
    SYSTEM_ERROR = "system_error"


@dataclass
class Alert:
    """An alert instance."""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    thread_id: Optional[str] = None
    acknowledged: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "thread_id": self.thread_id,
            "acknowledged": self.acknowledged
        }


class AlertManager:
    """
    Manages alerts and notifications.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize alert manager.
        
        Args:
            log_dir: Directory for alert logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create dedicated alerts log
        self.alerts_log_path = self.log_dir / "alerts.log"
        
        # Set up file handler
        self.file_handler = logging.FileHandler(self.alerts_log_path)
        self.file_handler.setLevel(logging.WARNING)
        
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        self.file_handler.setFormatter(formatter)
        
        # Add handler to alerts logger
        alerts_logger = logging.getLogger("alerts")
        alerts_logger.addHandler(self.file_handler)
        alerts_logger.setLevel(logging.INFO)
        
        # In-memory alert storage (recent alerts)
        self.active_alerts: List[Alert] = []
        self.max_active_alerts = 100
        
        logger.info(f"Alert manager initialized: {self.alerts_log_path}")
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Alert:
        """
        Create and log an alert.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            details: Additional details
            thread_id: Optional thread identifier
            
        Returns:
            Created Alert
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details,
            timestamp=datetime.utcnow(),
            thread_id=thread_id
        )
        
        # Add to active alerts
        self.active_alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.active_alerts) > self.max_active_alerts:
            self.active_alerts = self.active_alerts[-self.max_active_alerts:]
        
        # Log to file
        self._log_alert(alert)
        
        # Log to Langfuse if enabled
        self._log_to_langfuse(alert)
        
        # Log to main logger
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(
            log_level,
            f"ALERT [{alert_type.value}]: {message}"
        )
        
        return alert
    
    def _log_alert(self, alert: Alert):
        """
        Log alert to file.
        
        Args:
            alert: Alert to log
        """
        import json
        
        alerts_logger = logging.getLogger("alerts")
        log_message = json.dumps(alert.to_dict())
        
        if alert.severity == AlertSeverity.CRITICAL:
            alerts_logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            alerts_logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            alerts_logger.warning(log_message)
        else:
            alerts_logger.info(log_message)
    
    def _log_to_langfuse(self, alert: Alert):
        """
        Log alert to Langfuse.
        
        Args:
            alert: Alert to log
        """
        try:
            from ..utils.langfuse_config import get_langfuse_client
            
            client = get_langfuse_client()
            if not client:
                return
            
            # Create Langfuse event
            client.event(
                name=f"alert_{alert.alert_type.value}",
                metadata={
                    "alert": True,
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    **alert.details
                },
                session_id=alert.thread_id,
                level=alert.severity.value
            )
            
        except Exception as e:
            logger.warning(f"Failed to log alert to Langfuse: {e}")
    
    def check_latency(self, latency_ms: float, thread_id: str):
        """
        Check latency and create alert if threshold exceeded.
        
        Args:
            latency_ms: Latency in milliseconds
            thread_id: Thread identifier
        """
        threshold = Config.LATENCY_ALERT_THRESHOLD_MS
        
        if latency_ms > threshold:
            self.create_alert(
                alert_type=AlertType.HIGH_LATENCY,
                severity=AlertSeverity.WARNING,
                message=f"High latency detected: {latency_ms:.0f}ms (threshold: {threshold}ms)",
                details={
                    "latency_ms": latency_ms,
                    "threshold_ms": threshold,
                    "exceeded_by_ms": latency_ms - threshold
                },
                thread_id=thread_id
            )
    
    def check_cost(self, cost_usd: float, thread_id: str):
        """
        Check cost and create alert if threshold exceeded.
        
        Args:
            cost_usd: Cost in USD
            thread_id: Thread identifier
        """
        threshold = Config.COST_ALERT_THRESHOLD_USD
        
        if cost_usd > threshold:
            self.create_alert(
                alert_type=AlertType.HIGH_COST,
                severity=AlertSeverity.WARNING,
                message=f"High cost detected: ${cost_usd:.4f} (threshold: ${threshold})",
                details={
                    "cost_usd": cost_usd,
                    "threshold_usd": threshold,
                    "exceeded_by_usd": cost_usd - threshold
                },
                thread_id=thread_id
            )
    
    def check_error_rate(self, error_rate: float):
        """
        Check error rate and create alert if too high.
        
        Args:
            error_rate: Error rate (0-1)
        """
        if error_rate > 0.05:  # >5% error rate
            severity = AlertSeverity.ERROR if error_rate > 0.10 else AlertSeverity.WARNING
            
            self.create_alert(
                alert_type=AlertType.HIGH_ERROR_RATE,
                severity=severity,
                message=f"High error rate: {error_rate:.1%}",
                details={
                    "error_rate": error_rate,
                    "threshold": 0.05
                }
            )
    
    def alert_safety_violation(
        self,
        violation_type: str,
        details: Dict[str, Any],
        thread_id: str
    ):
        """
        Create alert for safety violation.
        
        Args:
            violation_type: Type of violation
            details: Violation details
            thread_id: Thread identifier
        """
        self.create_alert(
            alert_type=AlertType.SAFETY_VIOLATION,
            severity=AlertSeverity.ERROR,
            message=f"Safety violation: {violation_type}",
            details=details,
            thread_id=thread_id
        )
    
    def alert_pii_detected(
        self,
        pii_types: List[str],
        risk_level: str,
        location: str,
        thread_id: str
    ):
        """
        Create alert for PII detection.
        
        Args:
            pii_types: List of detected PII types
            risk_level: Risk level
            location: Where PII was detected
            thread_id: Thread identifier
        """
        # Only alert on high-risk PII
        if risk_level in ['medium', 'high']:
            severity = AlertSeverity.ERROR if risk_level == 'high' else AlertSeverity.WARNING
            
            self.create_alert(
                alert_type=AlertType.PII_DETECTED,
                severity=severity,
                message=f"PII detected in {location}: {', '.join(pii_types)} (risk: {risk_level})",
                details={
                    "pii_types": pii_types,
                    "risk_level": risk_level,
                    "location": location
                },
                thread_id=thread_id
            )
    
    def alert_low_quality(
        self,
        quality_score: float,
        issues: List[str],
        thread_id: str
    ):
        """
        Create alert for low quality response.
        
        Args:
            quality_score: Quality score
            issues: List of quality issues
            thread_id: Thread identifier
        """
        self.create_alert(
            alert_type=AlertType.LOW_QUALITY,
            severity=AlertSeverity.WARNING,
            message=f"Low quality response: score={quality_score:.2f}",
            details={
                "quality_score": quality_score,
                "issues": issues,
                "threshold": Config.QUALITY_SCORE_THRESHOLD
            },
            thread_id=thread_id
        )
    
    def alert_system_error(
        self,
        error_type: str,
        error_message: str,
        thread_id: Optional[str] = None
    ):
        """
        Create alert for system error.
        
        Args:
            error_type: Type of error
            error_message: Error message
            thread_id: Optional thread identifier
        """
        self.create_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            severity=AlertSeverity.ERROR,
            message=f"System error: {error_type}",
            details={
                "error_type": error_type,
                "error_message": error_message
            },
            thread_id=thread_id
        )
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        unacknowledged_only: bool = False
    ) -> List[Alert]:
        """
        Get active alerts with optional filters.
        
        Args:
            severity: Filter by severity
            alert_type: Filter by type
            unacknowledged_only: Only return unacknowledged alerts
            
        Returns:
            List of alerts
        """
        alerts = self.active_alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        return alerts
    
    def acknowledge_alert(self, alert: Alert):
        """
        Acknowledge an alert.
        
        Args:
            alert: Alert to acknowledge
        """
        alert.acknowledged = True
        logger.info(f"Alert acknowledged: {alert.alert_type.value}")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary of alerts.
        
        Returns:
            Dictionary with alert statistics
        """
        total = len(self.active_alerts)
        unacknowledged = sum(1 for a in self.active_alerts if not a.acknowledged)
        
        # Count by severity
        by_severity = {}
        for severity in AlertSeverity:
            count = sum(1 for a in self.active_alerts if a.severity == severity)
            by_severity[severity.value] = count
        
        # Count by type
        by_type = {}
        for alert_type in AlertType:
            count = sum(1 for a in self.active_alerts if a.alert_type == alert_type)
            by_type[alert_type.value] = count
        
        # Recent alerts (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = sum(
            1 for a in self.active_alerts
            if a.timestamp >= one_hour_ago
        )
        
        return {
            "total_alerts": total,
            "unacknowledged": unacknowledged,
            "recent_hour": recent_count,
            "by_severity": by_severity,
            "by_type": by_type
        }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """
    Get the global alert manager instance.
    
    Returns:
        AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager

