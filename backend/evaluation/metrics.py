"""
Performance metrics collection and analysis.

Tracks latency, cost, error rates, and operational metrics.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics tracked."""
    LATENCY = "latency"
    COST = "cost"
    ERROR = "error"
    SUCCESS = "success"
    TOKEN_USAGE = "token_usage"


@dataclass
class PerformanceMetrics:
    """Performance metrics for a request."""
    total_latency_ms: float
    node_latencies: Dict[str, float] = field(default_factory=dict)
    token_count: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    error_occurred: bool = False
    error_type: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_latency_ms": self.total_latency_ms,
            "node_latencies": self.node_latencies,
            "token_count": self.token_count,
            "estimated_cost_usd": self.estimated_cost_usd,
            "error_occurred": self.error_occurred,
            "error_type": self.error_type
        }


@dataclass
class ErrorMetrics:
    """Error tracking metrics."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    out_of_scope: int = 0
    context_drift: int = 0
    api_errors: int = 0
    timeouts: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_queries == 0:
            return 0.0
        return self.successful_queries / self.total_queries
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return 1.0 - self.success_rate
    
    @property
    def out_of_scope_rate(self) -> float:
        """Calculate out-of-scope rate."""
        if self.total_queries == 0:
            return 0.0
        return self.out_of_scope / self.total_queries
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "out_of_scope": self.out_of_scope,
            "out_of_scope_rate": self.out_of_scope_rate,
            "context_drift": self.context_drift,
            "api_errors": self.api_errors,
            "timeouts": self.timeouts
        }


class LatencyTracker:
    """
    Track latency metrics with percentile calculations.
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize latency tracker.
        
        Args:
            window_size: Number of samples to keep in rolling window
        """
        self.window_size = window_size
        self.latencies: List[float] = []
    
    def record(self, latency_ms: float):
        """
        Record a latency measurement.
        
        Args:
            latency_ms: Latency in milliseconds
        """
        self.latencies.append(latency_ms)
        
        # Keep only recent samples
        if len(self.latencies) > self.window_size:
            self.latencies = self.latencies[-self.window_size:]
    
    def get_percentile(self, percentile: float) -> float:
        """
        Calculate latency percentile.
        
        Args:
            percentile: Percentile to calculate (e.g., 0.95 for p95)
            
        Returns:
            Latency at given percentile
        """
        if not self.latencies:
            return 0.0
        
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * percentile)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    def get_stats(self) -> Dict[str, float]:
        """
        Get latency statistics.
        
        Returns:
            Dictionary with latency stats
        """
        if not self.latencies:
            return {
                "count": 0,
                "mean": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "max": 0
            }
        
        return {
            "count": len(self.latencies),
            "mean": sum(self.latencies) / len(self.latencies),
            "p50": self.get_percentile(0.50),
            "p95": self.get_percentile(0.95),
            "p99": self.get_percentile(0.99),
            "max": max(self.latencies)
        }


class CostEstimator:
    """
    Estimate costs for LLM and search API calls.
    """
    
    # Pricing (approximate, update with actual rates)
    VERTEX_AI_SEARCH_COST_PER_QUERY = 0.005  # $0.005 per query
    GEMINI_INPUT_COST_PER_1K_TOKENS = 0.0001  # $0.0001 per 1K tokens
    GEMINI_OUTPUT_COST_PER_1K_TOKENS = 0.0003  # $0.0003 per 1K tokens
    
    def estimate_query_cost(
        self,
        search_calls: int = 1,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> float:
        """
        Estimate cost for a query.
        
        Args:
            search_calls: Number of Vertex AI Search calls
            input_tokens: Total input tokens to LLM
            output_tokens: Total output tokens from LLM
            
        Returns:
            Estimated cost in USD
        """
        search_cost = search_calls * self.VERTEX_AI_SEARCH_COST_PER_QUERY
        llm_cost = (
            (input_tokens / 1000) * self.GEMINI_INPUT_COST_PER_1K_TOKENS +
            (output_tokens / 1000) * self.GEMINI_OUTPUT_COST_PER_1K_TOKENS
        )
        
        return search_cost + llm_cost
    
    def check_cost_threshold(self, cost_usd: float) -> bool:
        """
        Check if cost exceeds threshold.
        
        Args:
            cost_usd: Cost in USD
            
        Returns:
            True if cost exceeds threshold
        """
        return cost_usd > Config.COST_ALERT_THRESHOLD_USD


class MetricsCollector:
    """
    Centralized metrics collection for the agent.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.latency_tracker = LatencyTracker()
        self.cost_estimator = CostEstimator()
        self.error_metrics = ErrorMetrics()
        
        # Node-specific latency tracking
        self.node_latencies: Dict[str, LatencyTracker] = defaultdict(LatencyTracker)
        
        # Cost tracking
        self.total_cost_usd: float = 0.0
        self.costs_by_thread: Dict[str, float] = defaultdict(float)
        
        # Tool usage tracking
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.tool_errors: Dict[str, int] = defaultdict(int)
        
        logger.info("Metrics collector initialized")
    
    def record_query(
        self,
        thread_id: str,
        latency_ms: float,
        success: bool,
        error_type: Optional[str] = None,
        node_latencies: Optional[Dict[str, float]] = None,
        estimated_cost: Optional[float] = None
    ):
        """
        Record metrics for a query.
        
        Args:
            thread_id: Thread identifier
            latency_ms: Total latency in milliseconds
            success: Whether query succeeded
            error_type: Type of error if failed
            node_latencies: Latency breakdown by node
            estimated_cost: Estimated cost
        """
        # Update error metrics
        self.error_metrics.total_queries += 1
        if success:
            self.error_metrics.successful_queries += 1
        else:
            self.error_metrics.failed_queries += 1
            
            # Categorize error
            if error_type == "out_of_scope":
                self.error_metrics.out_of_scope += 1
            elif error_type == "context_drift":
                self.error_metrics.context_drift += 1
            elif error_type == "timeout":
                self.error_metrics.timeouts += 1
            elif error_type:
                self.error_metrics.api_errors += 1
        
        # Record latency
        self.latency_tracker.record(latency_ms)
        
        # Record node latencies
        if node_latencies:
            for node_name, node_latency in node_latencies.items():
                self.node_latencies[node_name].record(node_latency)
        
        # Record cost
        if estimated_cost:
            self.total_cost_usd += estimated_cost
            self.costs_by_thread[thread_id] += estimated_cost
    
    def record_tool_usage(self, tool_name: str, success: bool):
        """
        Record tool usage.
        
        Args:
            tool_name: Name of tool
            success: Whether tool call succeeded
        """
        self.tool_usage[tool_name] += 1
        if not success:
            self.tool_errors[tool_name] += 1
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """
        Get real-time metrics snapshot.
        
        Returns:
            Dictionary with current metrics
        """
        latency_stats = self.latency_tracker.get_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "latency": latency_stats,
            "errors": self.error_metrics.to_dict(),
            "cost": {
                "total_usd": round(self.total_cost_usd, 4),
                "avg_per_query": (
                    round(self.total_cost_usd / self.error_metrics.total_queries, 4)
                    if self.error_metrics.total_queries > 0 else 0
                )
            },
            "tool_usage": dict(self.tool_usage),
            "tool_errors": dict(self.tool_errors),
            "health": self._calculate_health_status(latency_stats)
        }
    
    def _calculate_health_status(self, latency_stats: Dict[str, float]) -> str:
        """
        Calculate overall system health status.
        
        Args:
            latency_stats: Latency statistics
            
        Returns:
            Health status: 'healthy', 'degraded', 'unhealthy'
        """
        # Check error rate
        if self.error_metrics.error_rate > 0.1:  # >10% errors
            return "unhealthy"
        
        # Check latency
        if latency_stats["p95"] > Config.LATENCY_ALERT_THRESHOLD_MS:
            return "degraded"
        
        # Check success rate
        if self.error_metrics.success_rate < 0.9:  # <90% success
            return "degraded"
        
        return "healthy"
    
    def get_node_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get per-node latency metrics.
        
        Returns:
            Dictionary of node metrics
        """
        return {
            node_name: tracker.get_stats()
            for node_name, tracker in self.node_latencies.items()
        }


class PerformanceTracker:
    """
    Context manager for tracking request performance.
    """
    
    def __init__(self, thread_id: str, operation: str = "query"):
        """
        Initialize performance tracker.
        
        Args:
            thread_id: Thread identifier
            operation: Operation being tracked
        """
        self.thread_id = thread_id
        self.operation = operation
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.node_times: Dict[str, float] = {}
        self.error_type: Optional[str] = None
        self.success: bool = True
    
    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and record metrics."""
        self.end_time = time.time()
        
        if exc_type is not None:
            self.success = False
            self.error_type = exc_type.__name__
        
        # Calculate latency
        latency_ms = (self.end_time - self.start_time) * 1000
        
        # Record to global metrics collector
        collector = get_metrics_collector()
        collector.record_query(
            thread_id=self.thread_id,
            latency_ms=latency_ms,
            success=self.success,
            error_type=self.error_type,
            node_latencies=self.node_times
        )
        
        # Log if slow
        if latency_ms > Config.LATENCY_ALERT_THRESHOLD_MS:
            logger.warning(
                f"Slow {self.operation}: {latency_ms:.0f}ms "
                f"(threshold: {Config.LATENCY_ALERT_THRESHOLD_MS}ms)"
            )
        
        # Don't suppress exceptions
        return False
    
    def record_node_time(self, node_name: str, duration_ms: float):
        """
        Record time for a specific node.
        
        Args:
            node_name: Name of the node
            duration_ms: Duration in milliseconds
        """
        self.node_times[node_name] = duration_ms


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

