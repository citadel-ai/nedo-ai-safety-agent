"""
Benchmark management for gold-standard test cases.

Allows SMEs to create, manage, and run benchmark tests for quality assurance.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from ..utils.logging_config import get_logger
from ..utils.config import Config

logger = get_logger(__name__)


@dataclass
class Benchmark:
    """A single benchmark test case."""
    id: str
    query: str
    context: Dict[str, str]  # visa_type, location, etc.
    expected_answer_elements: List[str]  # Key facts that should be in answer
    must_include_citations: bool
    category: str  # e.g., 'visa-renewal', 'residence-registration'
    created_by: str  # SME email or identifier
    created_at: str  # ISO timestamp
    tags: List[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BenchmarkResult:
    """Result of running a benchmark."""
    benchmark_id: str
    passed: bool
    score: float  # 0-1
    actual_answer: str
    citations_count: int
    matched_elements: List[str]  # Which expected elements were found
    missing_elements: List[str]  # Which expected elements were missing
    quality_score: float  # From quality evaluator
    timestamp: str
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class BenchmarkManager:
    """
    Manages benchmark test cases and execution.
    """
    
    def __init__(self, benchmarks_dir: str = "data/benchmarks"):
        """
        Initialize benchmark manager.
        
        Args:
            benchmarks_dir: Directory for benchmark files
        """
        self.benchmarks_dir = Path(benchmarks_dir)
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        
        self.benchmarks_file = self.benchmarks_dir / "gold_standard.json"
        self.results_file = self.benchmarks_dir / "results.json"
        
        # Load existing benchmarks
        self.benchmarks: Dict[str, Benchmark] = {}
        self.load_benchmarks()
        
        logger.info(f"Benchmark manager initialized: {len(self.benchmarks)} benchmarks loaded")
    
    def load_benchmarks(self):
        """Load benchmarks from file."""
        if not self.benchmarks_file.exists():
            logger.info("No existing benchmarks file, starting fresh")
            self.benchmarks = {}
            return
        
        try:
            with open(self.benchmarks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert to Benchmark objects
            self.benchmarks = {}
            for b_dict in data.get("benchmarks", []):
                benchmark = Benchmark(**b_dict)
                self.benchmarks[benchmark.id] = benchmark
                
            logger.info(f"Loaded {len(self.benchmarks)} benchmarks")
            
        except Exception as e:
            logger.error(f"Failed to load benchmarks: {e}")
            self.benchmarks = {}
    
    def save_benchmarks(self):
        """Save benchmarks to file."""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "benchmarks": [b.to_dict() for b in self.benchmarks.values()]
            }
            
            with open(self.benchmarks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(self.benchmarks)} benchmarks")
            
        except Exception as e:
            logger.error(f"Failed to save benchmarks: {e}")
    
    def create_benchmark(
        self,
        query: str,
        context: Dict[str, str],
        expected_answer_elements: List[str],
        category: str,
        created_by: str,
        must_include_citations: bool = True,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Benchmark:
        """
        Create a new benchmark.
        
        Args:
            query: User query
            context: Context (visa_type, location)
            expected_answer_elements: Key facts that should be in answer
            category: Category (e.g., 'visa-renewal')
            created_by: SME identifier
            must_include_citations: Whether citations are required
            tags: Optional tags
            notes: Optional notes
            
        Returns:
            Created Benchmark
        """
        # Generate ID
        benchmark_id = self._generate_benchmark_id(category)
        
        benchmark = Benchmark(
            id=benchmark_id,
            query=query,
            context=context,
            expected_answer_elements=expected_answer_elements,
            must_include_citations=must_include_citations,
            category=category,
            created_by=created_by,
            created_at=datetime.utcnow().isoformat(),
            tags=tags or [],
            notes=notes
        )
        
        self.benchmarks[benchmark_id] = benchmark
        self.save_benchmarks()
        
        logger.info(f"Created benchmark: {benchmark_id}")
        return benchmark
    
    def _generate_benchmark_id(self, category: str) -> str:
        """
        Generate unique benchmark ID.
        
        Args:
            category: Benchmark category
            
        Returns:
            Unique ID
        """
        # Count existing benchmarks in category
        category_count = sum(
            1 for b in self.benchmarks.values()
            if b.category == category
        )
        
        # Format: category-XXX (e.g., visa-renewal-001)
        return f"{category}-{category_count + 1:03d}"
    
    def get_benchmark(self, benchmark_id: str) -> Optional[Benchmark]:
        """
        Get a benchmark by ID.
        
        Args:
            benchmark_id: Benchmark ID
            
        Returns:
            Benchmark or None
        """
        return self.benchmarks.get(benchmark_id)
    
    def list_benchmarks(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Benchmark]:
        """
        List benchmarks with optional filters.
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            
        Returns:
            List of benchmarks
        """
        results = list(self.benchmarks.values())
        
        if category:
            results = [b for b in results if b.category == category]
        
        if tags:
            results = [
                b for b in results
                if any(tag in b.tags for tag in tags)
            ]
        
        return results
    
    def update_benchmark(
        self,
        benchmark_id: str,
        **updates
    ) -> Optional[Benchmark]:
        """
        Update an existing benchmark.
        
        Args:
            benchmark_id: Benchmark ID
            **updates: Fields to update
            
        Returns:
            Updated benchmark or None
        """
        benchmark = self.benchmarks.get(benchmark_id)
        if not benchmark:
            logger.warning(f"Benchmark not found: {benchmark_id}")
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(benchmark, key):
                setattr(benchmark, key, value)
        
        self.save_benchmarks()
        logger.info(f"Updated benchmark: {benchmark_id}")
        
        return benchmark
    
    def delete_benchmark(self, benchmark_id: str) -> bool:
        """
        Delete a benchmark.
        
        Args:
            benchmark_id: Benchmark ID
            
        Returns:
            True if deleted, False if not found
        """
        if benchmark_id in self.benchmarks:
            del self.benchmarks[benchmark_id]
            self.save_benchmarks()
            logger.info(f"Deleted benchmark: {benchmark_id}")
            return True
        
        logger.warning(f"Benchmark not found: {benchmark_id}")
        return False
    
    def run_benchmark(
        self,
        benchmark: Benchmark,
        agent_function  # Function that takes (query, context) and returns response
    ) -> BenchmarkResult:
        """
        Run a single benchmark test.
        
        Args:
            benchmark: Benchmark to run
            agent_function: Function to test
            
        Returns:
            BenchmarkResult
        """
        try:
            logger.info(f"Running benchmark: {benchmark.id}")
            
            # Run agent
            result = agent_function(benchmark.query, benchmark.context)
            
            # Extract response details
            answer = result.get("answer", "")
            citations = result.get("citations", [])
            error = result.get("error")
            
            if error:
                return BenchmarkResult(
                    benchmark_id=benchmark.id,
                    passed=False,
                    score=0.0,
                    actual_answer=answer,
                    citations_count=len(citations),
                    matched_elements=[],
                    missing_elements=benchmark.expected_answer_elements,
                    quality_score=0.0,
                    timestamp=datetime.utcnow().isoformat(),
                    error=error
                )
            
            # Check expected elements
            matched_elements = []
            missing_elements = []
            
            answer_lower = answer.lower()
            for element in benchmark.expected_answer_elements:
                # Simple substring matching (can be improved with semantic matching)
                if element.lower() in answer_lower:
                    matched_elements.append(element)
                else:
                    missing_elements.append(element)
            
            # Calculate score
            element_score = len(matched_elements) / len(benchmark.expected_answer_elements)
            
            # Check citations requirement
            has_citations = len(citations) > 0
            citations_pass = (not benchmark.must_include_citations) or has_citations
            
            # Overall score
            score = element_score if citations_pass else element_score * 0.5
            
            # Pass threshold
            passed = score >= 0.8 and citations_pass
            
            # Get quality score from result metadata if available
            quality_score = result.get("quality_score", score)
            
            result = BenchmarkResult(
                benchmark_id=benchmark.id,
                passed=passed,
                score=score,
                actual_answer=answer[:500],  # Truncate for storage
                citations_count=len(citations),
                matched_elements=matched_elements,
                missing_elements=missing_elements,
                quality_score=quality_score,
                timestamp=datetime.utcnow().isoformat()
            )
            
            logger.info(
                f"Benchmark {benchmark.id}: {'PASS' if passed else 'FAIL'} "
                f"(score: {score:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error running benchmark {benchmark.id}: {e}")
            return BenchmarkResult(
                benchmark_id=benchmark.id,
                passed=False,
                score=0.0,
                actual_answer="",
                citations_count=0,
                matched_elements=[],
                missing_elements=benchmark.expected_answer_elements,
                quality_score=0.0,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e)
            )
    
    def run_benchmark_suite(
        self,
        agent_function,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[BenchmarkResult]:
        """
        Run multiple benchmarks.
        
        Args:
            agent_function: Function to test
            category: Optional category filter
            tags: Optional tags filter
            
        Returns:
            List of BenchmarkResults
        """
        benchmarks = self.list_benchmarks(category=category, tags=tags)
        
        if not benchmarks:
            logger.warning("No benchmarks to run")
            return []
        
        logger.info(f"Running {len(benchmarks)} benchmarks...")
        
        results = []
        for benchmark in benchmarks:
            result = self.run_benchmark(benchmark, agent_function)
            results.append(result)
        
        # Save results
        self._save_results(results)
        
        # Log summary
        passed = sum(1 for r in results if r.passed)
        logger.info(
            f"Benchmark suite complete: {passed}/{len(results)} passed "
            f"({passed/len(results)*100:.1f}%)"
        )
        
        return results
    
    def _save_results(self, results: List[BenchmarkResult]):
        """
        Save benchmark results to file.
        
        Args:
            results: List of results to save
        """
        try:
            # Load existing results
            if self.results_file.exists():
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"runs": []}
            
            # Add new run
            run = {
                "timestamp": datetime.utcnow().isoformat(),
                "results": [r.to_dict() for r in results]
            }
            data["runs"].append(run)
            
            # Keep only last 50 runs
            if len(data["runs"]) > 50:
                data["runs"] = data["runs"][-50:]
            
            # Save
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def get_results_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get historical benchmark results.
        
        Args:
            limit: Number of runs to return
            
        Returns:
            List of run data
        """
        if not self.results_file.exists():
            return []
        
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            runs = data.get("runs", [])
            return runs[-limit:]
            
        except Exception as e:
            logger.error(f"Failed to load results history: {e}")
            return []


# Global benchmark manager instance
_benchmark_manager: Optional[BenchmarkManager] = None


def get_benchmark_manager() -> BenchmarkManager:
    """
    Get the global benchmark manager instance.
    
    Returns:
        BenchmarkManager instance
    """
    global _benchmark_manager
    if _benchmark_manager is None:
        _benchmark_manager = BenchmarkManager()
    return _benchmark_manager

