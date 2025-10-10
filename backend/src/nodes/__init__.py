"""
LangGraph nodes for Japan Helpdesk workflow.

Organized by workflow phase:
- intake: Intake & Validation
- search: Search
- processing: Processing & Formatting
- response: Response Validation & Synthesis
"""

# Phase 1: Intake & Validation
from .intake import (
    adversarial_detector_node,
    intake_agent_node,
    scope_checker_node,
)

# Phase 3: Processing & Formatting
from .processing import procedure_formatter_node

# Phase 4: Response Validation & Synthesis
from .response import (
    grounding_validator_node,
    legal_checker_node,
    response_synthesizer_node,
)

# Phase 2: Search
from .search import query_synthesizer_node, search_node

__all__ = [
    # Phase 1
    "adversarial_detector_node",
    "grounding_validator_node",
    "intake_agent_node",
    # Phase 4
    "legal_checker_node",
    # Phase 3
    "procedure_formatter_node",
    "query_synthesizer_node",
    "response_synthesizer_node",
    "scope_checker_node",
    # Phase 2
    "search_node",
]
