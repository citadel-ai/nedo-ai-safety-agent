"""Circuit Breaker Pattern - Prevent cascading failures in LLM calls."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 3  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout: float = 30.0  # Seconds before trying half-open


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, calls go through
    - OPEN: Too many failures, reject calls immediately
    - HALF_OPEN: Testing if system recovered, allow limited calls
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""

        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if self._should_attempt_reset():
                logger.info(
                    f"🔄 Circuit breaker '{self.name}' attempting reset (HALF_OPEN)"
                )
                self.state = CircuitState.HALF_OPEN
            else:
                # Reject call
                time_remaining = self.config.timeout - (
                    time.time() - self.last_failure_time
                )
                logger.error(
                    f"⛔ Circuit breaker '{self.name}' OPEN - rejecting call (retry in {time_remaining:.1f}s)"
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Too many recent failures. Retry in {time_remaining:.1f}s"
                )

        try:
            # Execute the function
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"✅ Circuit breaker '{self.name}' success in HALF_OPEN ({self.success_count}/{self.config.success_threshold})"
            )

            if self.success_count >= self.config.success_threshold:
                logger.info(
                    f"🟢 Circuit breaker '{self.name}' CLOSED - system recovered"
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            # Reset failure count on success in CLOSED state
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"❌ Circuit breaker '{self.name}' failure ({self.failure_count}/{self.config.failure_threshold})"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Failed during testing, go back to OPEN
            logger.error(f"🔴 Circuit breaker '{self.name}' OPEN - recovery failed")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.config.failure_threshold:
            # Too many failures, open the circuit
            logger.error(
                f"🔴 Circuit breaker '{self.name}' OPEN - failure threshold reached"
            )
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if not self.last_failure_time:
            return True
        return (time.time() - self.last_failure_time) >= self.config.timeout

    def reset(self):
        """Manually reset circuit breaker."""
        logger.info(f"🔄 Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    @property
    def is_available(self) -> bool:
        """Check if circuit breaker allows calls."""
        if self.state == CircuitState.OPEN:
            return self._should_attempt_reset()
        return True


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    pass


# Global circuit breakers for different LLM operations
_circuit_breakers = {}


def get_circuit_breaker(
    name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def protected_llm_call(
    circuit_name: str,
    func: Callable,
    fallback_func: Callable | None = None,
    *args,
    **kwargs,
) -> Any:
    """
    Execute LLM call with circuit breaker protection.

    Args:
        circuit_name: Name of the circuit breaker to use
        func: The function to call
        fallback_func: Optional fallback function if circuit is open
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func or fallback_func
    """
    breaker = get_circuit_breaker(circuit_name)

    try:
        return breaker.call(func, *args, **kwargs)
    except CircuitBreakerOpenError as e:
        logger.error(f"Circuit breaker open: {e}")
        if fallback_func:
            logger.info(f"Using fallback for '{circuit_name}'")
            return fallback_func(*args, **kwargs)
        raise


def get_all_circuit_breaker_status() -> dict:
    """Get status of all circuit breakers."""
    return {
        name: {
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
            "is_available": breaker.is_available,
        }
        for name, breaker in _circuit_breakers.items()
    }
