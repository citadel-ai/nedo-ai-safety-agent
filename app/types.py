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

from typing import List, Optional, Dict, Any, TypedDict, Annotated
from pydantic import BaseModel, Field
import operator


# Pydantic models for structured data
class AdversarialInputResult(BaseModel):
    """Result of adversarial input detection."""

    is_adversarial: bool = Field(description="True if input is adversarial/malicious")
    threat_type: Optional[str] = Field(
        default=None, description="Type of threat detected"
    )
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    reason: str = Field(description="Explanation of why input was flagged or approved")
    sanitized_query: Optional[str] = Field(
        default=None, description="Cleaned version if applicable"
    )


class IntakeSession(BaseModel):
    """Enhanced session state for intelligent intake agent."""

    session_id: str = Field(description="Unique session identifier")
    user_id: str = Field(description="User identifier")
    conversation_history: List[str] = Field(
        default_factory=list, description="Previous exchanges"
    )
    conversation_summary: str = Field(
        default="", description="Rolling summary of the conversation for context"
    )
    collected_info: Dict[str, Any] = Field(
        default_factory=dict, description="Information gathered"
    )
    current_step: str = Field(
        default="initial", description="Current step in intake process"
    )
    completed_steps: List[str] = Field(
        default_factory=list, description="Steps completed"
    )
    needs_clarification: List[str] = Field(
        default_factory=list, description="Items needing clarification"
    )
    is_complete: bool = Field(default=False, description="Whether intake is complete")

    # Structured context fields for downstream agents
    user_location: Optional[str] = Field(
        default=None, description="City/Prefecture in Japan"
    )
    visa_type: Optional[str] = Field(
        default=None, description="Type of visa (Student, Work, Tourist, etc.)"
    )
    current_status: Optional[str] = Field(
        default=None, description="Current visa/legal status"
    )
    timeline: Optional[str] = Field(
        default=None, description="When they need this resolved"
    )
    urgency_level: Optional[str] = Field(
        default=None, description="Low, Medium, High, Critical"
    )
    language_preference: Optional[str] = Field(
        default=None, description="Preferred language for assistance"
    )
    previous_attempts: Optional[str] = Field(
        default=None, description="What they've already tried"
    )
    specific_office_needed: Optional[str] = Field(
        default=None, description="Specific government office they need"
    )

    # Context analysis
    required_context_fields: List[str] = Field(
        default_factory=list, description="Context fields needed for this query"
    )
    missing_context_fields: List[str] = Field(
        default_factory=list, description="Still missing context"
    )
    context_completeness_score: float = Field(
        default=0.0, description="How complete the context is (0-1)"
    )

    # Intelligent questioning
    next_questions: List[str] = Field(
        default_factory=list, description="Next questions to ask"
    )
    question_priority: Dict[str, int] = Field(
        default_factory=dict, description="Priority of each question type"
    )
    suggested_answers: List[str] = Field(
        default_factory=list,
        description="Quick-reply suggestions for the current question",
    )


class ScopeCheckResult(BaseModel):
    """Result of scope checking for legal queries."""

    is_in_scope: bool = Field(description="Whether query is within supported scope")
    category: Optional[str] = Field(description="Category of the query")
    reason: Optional[str] = Field(description="Reason for rejection if out of scope")
    confidence: float = Field(description="Confidence score between 0 and 1")


class VectorSearchResult(BaseModel):
    """Result from vector database search."""

    content: str = Field(description="Retrieved content")
    metadata: Dict[str, Any] = Field(description="Document metadata")
    similarity_score: float = Field(description="Similarity score")
    source: str = Field(description="Source document/URL")


class MergedSearchResult(BaseModel):
    """Merged result from vector DB and Google Search."""

    vector_results: List[VectorSearchResult] = Field(
        description="Results from vector database"
    )
    google_results: List[str] = Field(description="Results from Google Search")
    merged_summary: str = Field(description="Synthesized summary of all results")
    confidence_score: float = Field(
        description="Overall confidence in the merged result"
    )
    sources: List[str] = Field(description="All sources used")
    recommendations: List[str] = Field(description="Actionable recommendations")


class ContactInfo(BaseModel):
    """Contact information for government offices or agencies."""

    name: str = Field(description="Name of the office or agency")
    phone: Optional[str] = Field(default=None, description="Phone number")
    address: Optional[str] = Field(default=None, description="Physical address")
    website: Optional[str] = Field(default=None, description="Website URL")
    hours: Optional[str] = Field(default=None, description="Operating hours")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class LegalResponse(BaseModel):
    """Structured response for legal queries."""

    summary: str = Field(description="Brief summary of the issue and guidance")
    disclaimers: List[str] = Field(description="Important disclaimers and limitations")
    next_steps: List[str] = Field(description="Recommended next steps for the user")
    useful_offices: List[ContactInfo] = Field(description="Relevant government offices")
    useful_phrases: List[str] = Field(description="Useful Japanese phrases")
    confidence_level: str = Field(description="Confidence level: high, medium, or low")
    sources: List[str] = Field(description="Sources of information used")


class LegalAdviceCheck(BaseModel):
    """Result of legal advice detection."""

    contains_legal_advice: bool = Field(
        description="Whether response contains legal advice"
    )
    problematic_phrases: List[str] = Field(description="List of problematic phrases")
    suggested_replacements: List[str] = Field(
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
    assigned_to: Optional[str] = Field(
        default=None, description="Which agent should handle this"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="TODO IDs this depends on"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context for the task"
    )
    tools_needed: List[str] = Field(
        default_factory=list, description="Tools required for this task"
    )
    estimated_effort: Optional[str] = Field(
        default=None, description="Estimated effort (low, medium, high)"
    )
    deadline: Optional[str] = Field(
        default=None, description="When this should be completed"
    )
    result: Optional[str] = Field(default=None, description="Result when completed")


class AgentPlan(BaseModel):
    """Agent's self-generated plan for handling a query."""

    plan_id: str = Field(description="Unique identifier for this plan")
    goal: str = Field(description="Overall goal the agent is trying to achieve")
    strategy: str = Field(description="High-level strategy for achieving the goal")
    todos: List[AgentTodo] = Field(
        default_factory=list, description="List of tasks to complete"
    )
    current_todo_id: Optional[str] = Field(
        default=None, description="Currently active TODO"
    )
    plan_status: str = Field(
        default="active", description="active, completed, failed, paused"
    )
    confidence_in_plan: float = Field(
        default=0.0, description="Agent's confidence in this plan (0-1)"
    )
    alternative_plans: List[str] = Field(
        default_factory=list, description="Alternative approaches considered"
    )


class JapanHelpdeskState(TypedDict):
    """Enhanced state for the Japan Helpdesk LangGraph workflow with agentic capabilities."""

    # Input and user information
    user_input: str
    user_id: str
    session_id: Optional[str]
    synthesized_search_query: Optional[str]  # Intelligent query for search

    # Workflow tracking
    current_step: str
    completed_steps: List[str]
    error_count: int

    # Agent results
    adversarial_result: Optional[AdversarialInputResult]
    intake_session: Optional[IntakeSession]
    scope_check_result: Optional[
        ScopeCheckResult
    ]  # Consistent key across nodes/routers
    vector_results: Optional[MergedSearchResult]
    hybrid_results: Optional[MergedSearchResult]
    rag_results: Optional[LegalResponse]
    legal_check_result: Optional[
        LegalAdviceCheck
    ]  # Consistent key across nodes/routers

    # Agentic capabilities
    agent_plan: Optional[AgentPlan]
    active_todos: List[AgentTodo]
    completed_todos: List[AgentTodo]
    agent_reasoning: List[str]  # Agent's reasoning steps
    tool_usage_log: List[Dict[str, Any]]  # Log of tools used and results

    # Final response
    final_response: Optional[str]
    confidence_score: float
    sources: List[str]  # Fixed: removed operator.add
    recommendations: List[str]  # Fixed: removed operator.add

    # Error handling
    errors: List[str]  # Fixed: removed operator.add
    fallback_used: bool

    # Observability metadata
    processing_time: float
    tokens_used: int
    langfuse_trace_id: Optional[str]

    # Agentic search results (internal)
    _raw_vector_results: Optional[List[Dict[str, Any]]]
    _raw_google_results: Optional[List[Any]]
    _procedure_breakdown: Optional[Any]


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
