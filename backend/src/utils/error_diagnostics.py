"""
Error Diagnostics - Comprehensive error tracking and debugging for workflow issues.
"""

import logging
import traceback
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowDiagnostics:
    """Tracks and diagnoses workflow execution issues."""

    def __init__(self):
        self.diagnostics = []

    def log_node_execution(
        self,
        node_name: str,
        state_before: dict[str, Any],
        state_after: dict[str, Any],
        success: bool,
        error: Exception | None = None,
    ):
        """Log detailed node execution information."""

        diagnostic = {
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "success": success,
            "state_changes": self._detect_state_changes(state_before, state_after),
            "error": str(error) if error else None,
            "traceback": traceback.format_exc() if error else None,
        }

        self.diagnostics.append(diagnostic)

        # Log immediately
        if success:
            logger.info(f"✅ {node_name} completed successfully")
            logger.debug(f"   State changes: {diagnostic['state_changes']}")
        else:
            logger.error(f"❌ {node_name} FAILED: {error}")
            logger.error(f"   Full traceback: {diagnostic['traceback']}")

    def _detect_state_changes(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> dict[str, str]:
        """Detect what changed in state."""
        changes = {}

        # Check key fields
        important_fields = [
            "final_response",
            "intake_session",
            "synthesized_search_query",
            "search_results",
            "recommendations",
            "errors",
        ]

        for field in important_fields:
            before_val = before.get(field)
            after_val = after.get(field)

            if before_val != after_val:
                changes[field] = (
                    f"{self._summarize_value(before_val)} → ",
                    f"{self._summarize_value(after_val)}",
                )

        return changes

    def _summarize_value(self, value: Any) -> str:
        """Create a short summary of a value."""
        if value is None:
            return "None"
        elif isinstance(value, str):
            return f"'{value[:50]}...'" if len(value) > 50 else f"'{value}'"
        elif isinstance(value, list):
            return f"[{len(value)} items]"
        elif isinstance(value, dict):
            return f"{{{len(value)} keys}}"
        elif hasattr(value, "__class__"):
            return f"<{value.__class__.__name__}>"
        else:
            return str(value)[:50]

    def get_failure_report(self) -> str:
        """Generate a detailed failure report."""
        failures = [d for d in self.diagnostics if not d["success"]]

        if not failures:
            return "No failures detected"

        report = ["=" * 60, "WORKFLOW FAILURE REPORT", "=" * 60]

        for i, failure in enumerate(failures, 1):
            report.append(f"\nFailure #{i}: {failure['node']}")
            report.append(f"Time: {failure['timestamp']}")
            report.append(f"Error: {failure['error']}")
            report.append(f"State changes: {failure['state_changes']}")
            if failure["traceback"]:
                report.append(f"Traceback:\n{failure['traceback']}")

        return "\n".join(report)


def diagnose_intake_failure(state: dict[str, Any]) -> str:
    """Diagnose why intake agent might have failed."""

    issues = []

    intake_session = state.get("intake_session")

    if not intake_session:
        issues.append("❌ No intake_session created")
    else:
        if not hasattr(intake_session, "next_questions"):
            issues.append("❌ intake_session missing 'next_questions' attribute")
        elif not intake_session.next_questions:
            issues.append("⚠️ intake_session.next_questions is empty")
            issues.append(
                f"   is_complete: {getattr(intake_session, 'is_complete', 'N/A')}"
            )
            issues.append(
                "   conversation_history: "
                f"{len(getattr(intake_session, 'conversation_history', []))} messages"
            )
            issues.append(
                "   required_context: "
                f"{getattr(intake_session, 'required_context_fields', [])}"
            )
            issues.append(
                "   missing_context: "
                f"{getattr(intake_session, 'missing_context_fields', [])}"
            )

    final_response = state.get("final_response")
    if not final_response:
        issues.append("❌ No final_response set")

    errors = state.get("errors", [])
    if errors:
        issues.append(f"⚠️ Errors in state: {errors}")

    return "\n".join(issues) if issues else "No obvious issues detected"


def diagnose_search_failure(state: dict[str, Any]) -> str:
    """Diagnose why search might have failed."""

    issues = []

    synthesized_query = state.get("synthesized_search_query")
    if not synthesized_query:
        issues.append("⚠️ No synthesized_search_query - using raw user_input")

    search_results = state.get("search_results")
    vector_results = state.get("_raw_vector_results")
    google_results = state.get("_raw_google_results")

    if not search_results and not vector_results and not google_results:
        issues.append("❌ No search results at all (RAG)")
    else:
        if search_results is not None:
            issues.append("✓ Search results available (merged RAG output)")
        if vector_results is not None:
            issues.append(f"✓ Vector DB results: {len(vector_results)} items")
        if google_results is not None:
            issues.append(f"✓ Google results: {len(google_results)} items")

    return "\n".join(issues) if issues else "Search appears to have run"


def diagnose_llm_truncation(
    response_content: str, max_expected: int = 1500
) -> str | None:
    """Diagnose if LLM response was truncated."""

    if len(response_content) < 100:
        return (
            f"⚠️ Response very short ({len(response_content)} chars) - may be truncated"
        )

    # Check if JSON is incomplete
    if "```json" in response_content:
        if not response_content.strip().endswith(
            "```"
        ) and not response_content.strip().endswith("}"):
            return "⚠️ JSON response appears incomplete - missing closing"

    # Check if response ends mid-field
    incomplete_indicators = [
        '"required_context_fields": [',
        '"next_questions": [',
        '"steps": [',
        ': "',  # Field started but not completed
    ]

    for indicator in incomplete_indicators:
        if response_content.rstrip().endswith(indicator):
            return f"⚠️ Response ends with '{indicator}' - likely truncated"

    return None


def create_detailed_error_response(
    state: dict[str, Any], stage: str, original_error: Exception | None = None
) -> str:
    """Create a detailed, helpful error response instead of generic apology."""

    response_parts = [
        "I encountered an issue while processing your request. Here's what I found:",
        "",
    ]

    # Identify the stage
    completed_steps = state.get("completed_steps", [])
    response_parts.append(f"**Processing Stage**: {stage}")
    response_parts.append(
        "**Completed Steps**: "
        f"{', '.join(completed_steps) if completed_steps else 'None'}"
    )
    response_parts.append("")

    # Stage-specific diagnostics
    if "intake" in stage.lower():
        response_parts.append("**Intake Agent Issue**:")
        response_parts.append(diagnose_intake_failure(state))
    elif "search" in stage.lower():
        response_parts.append("**Search Issue**:")
        response_parts.append(diagnose_search_failure(state))

    # Include actual error if available
    if original_error:
        response_parts.append("")
        response_parts.append(
            f"**Technical Error**: {type(original_error).__name__}: {original_error!s}"
        )

    # State errors
    errors = state.get("errors", [])
    if errors:
        response_parts.append("")
        response_parts.append("**Recorded Errors**:")
        for error in errors[-3:]:  # Last 3 errors
            response_parts.append(f"- {error}")

    # Helpful suggestion
    response_parts.append("")
    response_parts.append("**What you can try**:")
    response_parts.append("1. Rephrase your question with more context")
    response_parts.append("2. Try a more specific question")
    response_parts.append("3. Break your question into smaller parts")

    return "\n".join(response_parts)


def validate_state_integrity(state: dict[str, Any]) -> list[str]:
    """Validate that state has all required fields and proper structure."""

    issues = []

    required_fields = [
        "user_input",
        "user_id",
        "session_id",
        "current_step",
        "completed_steps",
        "errors",
        "final_response",
    ]

    for field in required_fields:
        if field not in state:
            issues.append(f"Missing required field: {field}")

    # Type checks
    if "completed_steps" in state and not isinstance(state["completed_steps"], list):
        issues.append(
            f"completed_steps should be list, got {type(state['completed_steps'])}"
        )

    if "errors" in state and not isinstance(state["errors"], list):
        issues.append(f"errors should be list, got {type(state['errors'])}")

    # Logical checks
    if state.get("error_count", 0) > 0 and not state.get("errors"):
        issues.append("error_count > 0 but errors list is empty")

    return issues
