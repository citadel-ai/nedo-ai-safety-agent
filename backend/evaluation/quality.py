"""
Quality evaluation module for task success tracking and accuracy scoring.

Implements quality metrics and evaluation logic following enterprise best practices.
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for a response."""
    citation_coverage: float  # 0-1
    completeness_score: float  # 0-1
    confidence_score: float  # 0-1
    quality_score: float  # 0-1, overall
    sme_rating: Optional[float] = None  # 1-5 if available
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "citation_coverage": self.citation_coverage,
            "completeness_score": self.completeness_score,
            "confidence_score": self.confidence_score,
            "quality_score": self.quality_score,
            "sme_rating": self.sme_rating,
            "issues": self.issues,
            "passed": self.quality_score >= Config.QUALITY_SCORE_THRESHOLD
        }


@dataclass
class TaskCompletionResult:
    """Result of task completion evaluation."""
    task_completed: bool
    completion_quality: float  # 0-1
    requires_followup: bool
    reasoning: str
    indicators: Dict[str, bool]  # What indicators were checked
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_completed": self.task_completed,
            "completion_quality": self.completion_quality,
            "requires_followup": self.requires_followup,
            "reasoning": self.reasoning,
            "indicators": self.indicators
        }


def calculate_quality_score(
    citation_coverage: float,
    llm_confidence: float,
    sme_rating: Optional[float] = None,
    completeness_score: float = 1.0
) -> float:
    """
    Calculate overall quality score for a response.
    
    Combines multiple quality signals:
    - Citation coverage (how well grounded in sources)
    - LLM confidence (from Vertex AI)
    - Completeness (did it answer the question)
    - SME rating (if available)
    
    Args:
        citation_coverage: Citation coverage score (0-1)
        llm_confidence: LLM confidence score (0-1)
        sme_rating: Optional SME rating (1-5 scale)
        completeness_score: Completeness score (0-1)
        
    Returns:
        Overall quality score (0-1)
    """
    # Automatic score (weighted average)
    auto_score = (
        citation_coverage * 0.4 +
        llm_confidence * 0.3 +
        completeness_score * 0.3
    )
    
    # If SME rating available, blend with automatic score
    if sme_rating is not None:
        # Convert SME rating from 1-5 to 0-1 scale
        sme_normalized = (sme_rating - 1) / 4
        # Give SME rating high weight (60%)
        return (auto_score * 0.4) + (sme_normalized * 0.6)
    
    return auto_score


class QualityEvaluator:
    """
    Quality evaluator for agent responses.
    
    Evaluates:
    - Task completion
    - Response accuracy
    - Citation coverage
    - Completeness
    """
    
    def __init__(self):
        """Initialize quality evaluator."""
        self.quality_threshold = Config.QUALITY_SCORE_THRESHOLD
        self.min_citation_coverage = Config.MIN_CITATION_COVERAGE
    
    def evaluate_response(
        self,
        query: str,
        response: str,
        citations: List[dict],
        metadata: Optional[Dict[str, Any]] = None
    ) -> QualityMetrics:
        """
        Evaluate quality of a response.
        
        Args:
            query: User query
            response: Agent response
            citations: List of citations
            metadata: Additional metadata (e.g., Vertex AI confidence)
            
        Returns:
            QualityMetrics with evaluation results
        """
        issues = []
        
        # Calculate citation coverage
        citation_coverage = self._calculate_citation_coverage(response, citations)
        if citation_coverage < self.min_citation_coverage:
            issues.append(f"Low citation coverage ({citation_coverage:.1%})")
        
        # Calculate completeness
        completeness_score = self._calculate_completeness(query, response)
        if completeness_score < 0.7:
            issues.append("Response may be incomplete")
        
        # Get confidence from metadata
        confidence_score = metadata.get("confidence", 0.8) if metadata else 0.8
        
        # Calculate overall quality score
        quality_score = calculate_quality_score(
            citation_coverage=citation_coverage,
            llm_confidence=confidence_score,
            completeness_score=completeness_score
        )
        
        if quality_score < self.quality_threshold:
            issues.append(f"Quality score below threshold ({quality_score:.2f} < {self.quality_threshold})")
        
        metrics = QualityMetrics(
            citation_coverage=citation_coverage,
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            quality_score=quality_score,
            issues=issues
        )
        
        if metrics.quality_score < self.quality_threshold:
            logger.warning(f"Low quality response: score={quality_score:.2f}, issues={issues}")
        
        return metrics
    
    def _calculate_citation_coverage(
        self,
        response: str,
        citations: List[dict]
    ) -> float:
        """
        Calculate citation coverage.
        
        Args:
            response: Response text
            citations: List of citations
            
        Returns:
            Citation coverage score (0-1)
        """
        import re
        
        if not citations or not response:
            return 0.0
        
        # Count citation markers in response
        citation_markers = re.findall(r'\[\d+\]', response)
        
        if not citation_markers:
            return 0.0
        
        # Calculate based on density
        words = len(response.split())
        expected_citations = max(words / 50, 1)  # 1 citation per 50 words
        actual_citations = len(set(citation_markers))
        
        coverage = min(actual_citations / expected_citations, 1.0)
        
        return coverage
    
    def _calculate_completeness(self, query: str, response: str) -> float:
        """
        Estimate completeness of response.
        
        Args:
            query: User query
            response: Agent response
            
        Returns:
            Completeness score (0-1)
        """
        # Basic heuristic: response should be substantial
        if len(response) < 50:
            return 0.3  # Very short response
        
        # Check for common incomplete patterns
        incomplete_patterns = [
            "I don't know",
            "I cannot",
            "I'm not sure",
            "insufficient information",
            "no information available"
        ]
        
        response_lower = response.lower()
        if any(pattern in response_lower for pattern in incomplete_patterns):
            return 0.6
        
        # Check if response has structure (multiple sentences/paragraphs)
        sentences = response.split('.')
        if len(sentences) < 3:
            return 0.7
        
        # If we got here, response seems complete
        return 0.9
    
    def evaluate_task_completion(
        self,
        query: str,
        response: str,
        conversation_length: int,
        error: Optional[str] = None
    ) -> TaskCompletionResult:
        """
        Evaluate whether the task was completed successfully.
        
        Args:
            query: User query
            response: Agent response
            conversation_length: Number of messages in conversation
            error: Error message if any
            
        Returns:
            TaskCompletionResult with evaluation
        """
        indicators = {}
        
        # Check if there was an error
        indicators["no_error"] = error is None
        
        # Check if response is out-of-scope message
        indicators["in_scope"] = "outside my area of expertise" not in response.lower()
        
        # Check if response has substantial content
        indicators["has_content"] = len(response) > 100
        
        # Check if this is first message (initial query)
        indicators["first_interaction"] = conversation_length <= 2
        
        # Determine if task completed
        task_completed = all([
            indicators["no_error"],
            indicators["in_scope"],
            indicators["has_content"]
        ])
        
        # Determine if follow-up needed
        requires_followup = (
            not task_completed or
            "Would you like" in response or
            "any other questions" in response.lower()
        )
        
        # Calculate completion quality
        if task_completed:
            completion_quality = 0.9 if not requires_followup else 0.7
        else:
            completion_quality = 0.3
        
        # Generate reasoning
        if not task_completed:
            failed_indicators = [k for k, v in indicators.items() if not v]
            reasoning = f"Task not completed. Failed indicators: {', '.join(failed_indicators)}"
        elif requires_followup:
            reasoning = "Task completed but follow-up may be needed"
        else:
            reasoning = "Task completed successfully"
        
        return TaskCompletionResult(
            task_completed=task_completed,
            completion_quality=completion_quality,
            requires_followup=requires_followup,
            reasoning=reasoning,
            indicators=indicators
        )
    
    def add_sme_rating(
        self,
        metrics: QualityMetrics,
        sme_rating: float,
        sme_comments: Optional[str] = None
    ) -> QualityMetrics:
        """
        Add SME rating to existing quality metrics.
        
        Args:
            metrics: Existing quality metrics
            sme_rating: SME rating (1-5 scale)
            sme_comments: Optional SME comments
            
        Returns:
            Updated quality metrics
        """
        # Validate rating
        if not (1 <= sme_rating <= 5):
            logger.warning(f"Invalid SME rating: {sme_rating}, must be 1-5")
            return metrics
        
        # Recalculate quality score with SME rating
        new_quality_score = calculate_quality_score(
            citation_coverage=metrics.citation_coverage,
            llm_confidence=metrics.confidence_score,
            sme_rating=sme_rating,
            completeness_score=metrics.completeness_score
        )
        
        # Update metrics
        metrics.sme_rating = sme_rating
        metrics.quality_score = new_quality_score
        
        if sme_comments:
            metrics.issues.append(f"SME: {sme_comments}")
        
        logger.info(
            f"SME rating added: {sme_rating}/5, "
            f"new quality score: {new_quality_score:.2f}"
        )
        
        return metrics


class QualityTracker:
    """
    Track quality metrics over time for analysis and reporting.
    """
    
    def __init__(self):
        """Initialize quality tracker."""
        self.metrics_history: List[Dict[str, Any]] = []
    
    def record_metrics(
        self,
        thread_id: str,
        query: str,
        metrics: QualityMetrics,
        timestamp: Optional[datetime] = None
    ):
        """
        Record quality metrics for a query.
        
        Args:
            thread_id: Thread identifier
            query: User query
            metrics: Quality metrics
            timestamp: Optional timestamp (defaults to now)
        """
        record = {
            "thread_id": thread_id,
            "query": query[:100],  # Truncate
            "timestamp": timestamp or datetime.utcnow(),
            "metrics": metrics.to_dict()
        }
        
        self.metrics_history.append(record)
        
        # Keep only last 1000 records in memory
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate aggregate statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.metrics_history:
            return {
                "total_queries": 0,
                "avg_quality_score": 0,
                "avg_citation_coverage": 0,
                "pass_rate": 0
            }
        
        total = len(self.metrics_history)
        
        # Calculate averages
        quality_scores = [r["metrics"]["quality_score"] for r in self.metrics_history]
        citation_coverages = [r["metrics"]["citation_coverage"] for r in self.metrics_history]
        passed = [r["metrics"]["passed"] for r in self.metrics_history]
        
        return {
            "total_queries": total,
            "avg_quality_score": sum(quality_scores) / total,
            "avg_citation_coverage": sum(citation_coverages) / total,
            "pass_rate": sum(passed) / total,
            "below_threshold_count": total - sum(passed)
        }


# Global quality tracker instance
_quality_tracker: Optional[QualityTracker] = None


def get_quality_tracker() -> QualityTracker:
    """
    Get the global quality tracker instance.
    
    Returns:
        QualityTracker instance
    """
    global _quality_tracker
    if _quality_tracker is None:
        _quality_tracker = QualityTracker()
    return _quality_tracker

