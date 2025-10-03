# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Types and state management for Japan Helpdesk LangGraph implementation."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


# Pydantic models for structured data
class AdversarialInputResult(BaseModel):
    """Result of adversarial input detection."""

    is_adversarial: bool = Field(description="True if input is adversarial/malicious")
    threat_type: str | None = Field(
        default=None, description="Type of threat detected"
    )
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    reason: str = Field(description="Explanation of why input was flagged or approved")
    sanitized_query: str | None = Field(
        default=None, description="Cleaned version if applicable"
    )


class IntakeSession(BaseModel):
    """Enhanced session state for intelligent intake agent."""

    session_id: str = Field(description="Unique session identifier")
    user_id: str = Field(description="User identifier")
    conversation_history: list[str] = Field(
        default_factory=list, description="Previous exchanges"
    )
    conversation_summary: str = Field(
        default="", description="Rolling summary of the conversation for context"
    )
    collected_info: dict[str, Any] = Field(
        default_factory=dict, description="Information gathered"
    )
    current_step: str = Field(
        default="initial", description="Current step in intake process"
    )
    completed_steps: list[str] = Field(
        default_factory=list, description="Steps completed"
    )
    needs_clarification: list[str] = Field(
        default_factory=list, description="Items needing clarification"
    )
    is_complete: bool = Field(default=False, description="Whether intake is complete")

    # Structured context fields for downstream agents
    user_location: str | None = Field(
        default=None, description="City/Prefecture in Japan"
    )
    visa_type: str | None = Field(
        default=None, description="Type of visa (Student, Work, Tourist, etc.)"
    )
    current_status: str | None = Field(
        default=None, description="Current visa/legal status"
    )
    timeline: str | None = Field(
        default=None, description="When they need this resolved"
    )
    urgency_level: str | None = Field(
        default=None, description="Low, Medium, High, Critical"
    )
    language_preference: str | None = Field(
        default=None, description="Preferred language for assistance"
    )
    previous_attempts: str | None = Field(
        default=None, description="What they've already tried"
    )
    specific_office_needed: str | None = Field(
        default=None, description="Specific government office they need"
    )

    # Context analysis
    required_context_fields: list[str] = Field(
        default_factory=list, description="Context fields needed for this query"
    )
    missing_context_fields: list[str] = Field(
        default_factory=list, description="Still missing context"
    )
    context_completeness_score: float = Field(
        default=0.0, description="How complete the context is (0-1)"
    )

    # Intelligent questioning
    next_questions: list[str] = Field(
        default_factory=list, description="Next questions to ask"
    )
    question_priority: dict[str, int] = Field(
        default_factory=dict, description="Priority of each question type"
    )
    suggested_answers: list[str] = Field(
        default_factory=list,
        description="Quick-reply suggestions for the current question",
    )


class ScopeCheckResult(BaseModel):
    """Result of scope checking for legal queries."""

    is_in_scope: bool = Field(description="Whether query is within supported scope")
    category: str | None = Field(description="Category of the query")
    reason: str | None = Field(description="Reason for rejection if out of scope")
    confidence: float = Field(description="Confidence score between 0 and 1")


class VectorSearchResult(BaseModel):
    """Result from vector database search."""

    content: str = Field(description="Retrieved content")
    metadata: dict[str, Any] = Field(description="Document metadata")
    similarity_score: float = Field(description="Similarity score")
    source: str = Field(description="Source document/URL")


class MergedSearchResult(BaseModel):
    """Merged result from vector DB and Google Search."""

    vector_results: list[VectorSearchResult] = Field(
        description="Results from vector database"
    )
    google_results: list[str] = Field(description="Results from Google Search")
    merged_summary: str = Field(description="Synthesized summary of all results")
    confidence_score: float = Field(
        description="Overall confidence in the merged result"
    )
    sources: list[str] = Field(description="All sources used")
    recommendations: list[str] = Field(description="Actionable recommendations")


class ContactInfo(BaseModel):
    """Contact information for government offices or agencies."""

    name: str = Field(description="Name of the office or agency")
    phone: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Physical address")
    website: str | None = Field(default=None, description="Website URL")
    hours: str | None = Field(default=None, description="Operating hours")
    notes: str | None = Field(default=None, description="Additional notes")


class LegalResponse(BaseModel):
    """Structured response for legal queries."""

    summary: str = Field(description="Brief summary of the issue and guidance")
    disclaimers: list[str] = Field(description="Important disclaimers and limitations")
    next_steps: list[str] = Field(description="Recommended next steps for the user")
    useful_offices: list[ContactInfo] = Field(description="Relevant government offices")
    useful_phrases: list[str] = Field(description="Useful Japanese phrases")
    confidence_level: str = Field(description="Confidence level: high, medium, or low")
    sources: list[str] = Field(description="Sources of information used")


class LegalAdviceCheck(BaseModel):
    """Result of legal advice detection."""

    contains_legal_advice: bool = Field(
        description="Whether response contains legal advice"
    )
    problematic_phrases: list[str] = Field(description="List of problematic phrases")
    suggested_replacements: list[str] = Field(
        description="Suggested neutral replacements"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")


# LangGraph State Definition
class AgentTodo(BaseModel):
    """Self-generated TODO item for autonomous agent behavior."""

    id: str = Field(description="Unique identifier for this TODO")
    task: str = Field(description="Description of the task to complete")
    priority: int = Field(description="Priority level (1=highest, 5=lowest)")
    status: str = Field(
        default="pending", description="pending, in_progress, completed, failed"
    )
    created_by: str = Field(description="Which agent/node created this TODO")
    assigned_to: str | None = Field(
        default=None, description="Which agent should handle this"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="TODO IDs this depends on"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for the task"
    )
    tools_needed: list[str] = Field(
        default_factory=list, description="Tools required for this task"
    )
    estimated_effort: str | None = Field(
        default=None, description="Estimated effort (low, medium, high)"
    )
    deadline: str | None = Field(
        default=None, description="When this should be completed"
    )
    result: str | None = Field(default=None, description="Result when completed")


class AgentPlan(BaseModel):
    """Agent's self-generated plan for handling a query."""

    plan_id: str = Field(description="Unique identifier for this plan")
    goal: str = Field(description="Overall goal the agent is trying to achieve")
    strategy: str = Field(description="High-level strategy for achieving the goal")
    todos: list[AgentTodo] = Field(
        default_factory=list, description="List of tasks to complete"
    )
    current_todo_id: str | None = Field(
        default=None, description="Currently active TODO"
    )
    plan_status: str = Field(
        default="active", description="active, completed, failed, paused"
    )
    confidence_in_plan: float = Field(
        default=0.0, description="Agent's confidence in this plan (0-1)"
    )
    alternative_plans: list[str] = Field(
        default_factory=list, description="Alternative approaches considered"
    )


class JapanHelpdeskState(TypedDict):
    """Enhanced state for the Japan Helpdesk LangGraph workflow with agentic capabilities."""

    # Input and user information
    user_input: str
    user_id: str
    session_id: str | None
    synthesized_search_query: str | None  # Intelligent query for search

    # Workflow tracking
    current_step: str
    completed_steps: list[str]
    error_count: int

    # Agent results
    adversarial_result: AdversarialInputResult | None
    intake_session: IntakeSession | None
    scope_check_result: ScopeCheckResult | None  # Consistent key across nodes/routers
    vector_results: MergedSearchResult | None
    hybrid_results: MergedSearchResult | None
    rag_results: LegalResponse | None
    legal_check_result: LegalAdviceCheck | None  # Consistent key across nodes/routers

    # Agentic capabilities
    agent_plan: AgentPlan | None
    active_todos: list[AgentTodo]
    completed_todos: list[AgentTodo]
    agent_reasoning: list[str]  # Agent's reasoning steps
    tool_usage_log: list[dict[str, Any]]  # Log of tools used and results

    # Final response
    final_response: str | None
    confidence_score: float
    sources: list[str]  # Fixed: removed operator.add
    recommendations: list[str]  # Fixed: removed operator.add

    # Error handling
    errors: list[str]  # Fixed: removed operator.add
    fallback_used: bool

    # Observability metadata
    processing_time: float
    tokens_used: int
    langfuse_trace_id: str | None

    # Agentic search results (internal)
    _raw_vector_results: list[dict[str, Any]] | None
    _raw_google_results: list[Any] | None
    _procedure_breakdown: Any | None


# Supported categories for legal queries
SUPPORTED_CATEGORIES = [
    "visa",
    "immigration",
    "housing",
    "tax",
    "employment",
    "healthcare",
    "banking",
    "education",
    "marriage",
    "driving_license",
    "residence_card",
    "pension",
    "insurance",
    "business_registration",
    "general_procedures",
]

# High-risk categories requiring extra scrutiny
HIGH_RISK_CATEGORIES = ["visa", "immigration", "tax", "legal_procedures"]
