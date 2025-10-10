"""
Grounding Validator Node - Ensures responses are grounded in retrieved sources.

This node validates that the final response is actually supported by the
retrieved context (RAG + Google Search results) and not hallucinated.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.models import JapanHelpdeskState
from src.utils.llm_factory import create_llm
from src.utils.node_helpers import handle_node_error, track_execution
from src.utils.observability import observe

logger = logging.getLogger(__name__)

llm = create_llm(temperature=0.0)  # Use zero temperature for objective evaluation


class GroundingCheck(BaseModel):
    """Result of grounding validation."""

    is_grounded: bool = Field(
        description="Whether the response is fully grounded in the provided sources"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the grounding assessment (0-1)",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="List of claims in the response that are not supported by sources",
    )
    supported_claims: list[str] = Field(
        default_factory=list,
        description="List of claims that are well-supported by sources",
    )
    reasoning: str = Field(description="Explanation of the grounding assessment")
    grounding_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of supported claims to total claims (0-1)",
    )


GROUNDING_VALIDATION_PROMPT = """You are a grounding validator. Your job is to verify if an AI assistant's response is fully supported by the provided source documents.

**Instructions:**
1. Extract all factual claims from the response
2. For each claim, check if it's directly supported by the sources
3. A claim is "supported" only if it can be directly traced to the source material
4. Generic statements like "you should consult" or "it's recommended" are acceptable
5. Specific facts, numbers, dates, procedures, or requirements MUST be in the sources

**Sources (Retrieved Context):**
{sources}

**AI Response to Validate:**
{response}

**Your Task:**
Analyze the response and provide:
1. A list of supported claims (with brief source reference)
2. A list of unsupported/hallucinated claims
3. Overall grounding score (0-1)
4. Is the response grounded? (true/false)
5. Confidence in your assessment (0-1)
6. Reasoning for your decision

**Output Format (JSON):**
{{
    "is_grounded": true/false,
    "confidence": 0.0-1.0,
    "unsupported_claims": ["claim 1", "claim 2"],
    "supported_claims": ["claim 1", "claim 2"],
    "reasoning": "explanation",
    "grounding_score": 0.0-1.0
}}

**Important:**
- Be strict: If a specific fact isn't in the sources, mark it as unsupported
- Be fair: Don't mark general advice as unsupported
- Consider partial grounding: A response can be mostly grounded with minor issues
"""


def _extract_sources_from_state(state: JapanHelpdeskState) -> str:
    """Extract all source documents from the state."""
    sources = []

    # Get vector search results
    if state.get("_raw_vector_results"):
        vector_results = state["_raw_vector_results"]
        sources.append("=== VECTOR DATABASE RESULTS ===")
        for i, result in enumerate(vector_results[:10], 1):  # Top 10
            content = result.content[:500]  # First 500 chars
            metadata = result.metadata
            sources.append(f"\n[Vector Source {i}]")
            sources.append(f"Category: {metadata.get('category', 'N/A')}")
            sources.append(f"Filename: {metadata.get('filename', 'N/A')}")
            sources.append(f"Content: {content}...")
            sources.append("")

    # Get Google search results
    if state.get("_raw_google_results"):
        google_results = state["_raw_google_results"]
        sources.append("\n=== GOOGLE SEARCH RESULTS ===")
        for i, result in enumerate(google_results[:10], 1):  # Top 10
            sources.append(f"\n[Google Source {i}]")
            sources.append(f"Content: {result[:500]}...")
            sources.append("")

    # Fallback to search_results if raw results not available
    if not sources and state.get("search_results"):
        search_results = state["search_results"]
        sources.append("=== SEARCH RESULTS (RAG) ===")
        sources.append(search_results.merged_summary)

    if not sources:
        return "No source documents available"

    return "\n".join(sources)


def _extract_response_text(state: JapanHelpdeskState) -> str:
    """Extract the final response text from state."""
    # Try to get the synthesized response
    if state.get("final_response"):
        return state["final_response"]

    # Fallback to procedure results
    if state.get("procedure_result"):
        procedure = state["procedure_result"]
        parts = []
        if procedure.overview:
            parts.append(procedure.overview)
        if procedure.steps:
            parts.extend(
                [f"Step {i + 1}: {step}" for i, step in enumerate(procedure.steps)]
            )
        return "\n".join(parts)

    return "No response available"


@observe(name="grounding_validator_node")
async def grounding_validator_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """
    Validates that the response is grounded in retrieved sources.

    This node:
    1. Extracts all source documents (Vector DB + Google Search)
    2. Extracts the final response
    3. Uses an LLM to verify each claim is supported by sources
    4. Provides a grounding score and identifies unsupported claims
    """
    try:
        with track_execution(state, "grounding_validation"):
            logger.info("🔍 GROUNDING VALIDATOR - Starting validation")

            # Extract sources and response
            sources = _extract_sources_from_state(state)
            response = _extract_response_text(state)

            if sources == "No source documents available":
                logger.warning("⚠️ No sources available for grounding validation")
                state["grounding_check"] = GroundingCheck(
                    is_grounded=False,
                    confidence=0.0,
                    unsupported_claims=["No sources available to validate against"],
                    supported_claims=[],
                    reasoning="Cannot validate grounding without source documents",
                    grounding_score=0.0,
                )
                return state

            logger.info(
                f"📄 Validating response ({len(response)} chars) against sources ({len(sources)} chars)"
            )

            # Prepare prompt
            prompt = GROUNDING_VALIDATION_PROMPT.format(
                sources=sources, response=response
            )

            messages = [
                SystemMessage(
                    content="You are a strict grounding validator for RAG systems."
                ),
                HumanMessage(content=prompt),
            ]

            # Get validation from LLM
            llm_response = await llm.ainvoke(messages)

            # Parse response
            try:
                import json
                import re

                # Extract JSON from response
                content = llm_response.content
                # Try to find JSON block
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    json_str = json_match.group(0)
                    result_data = json.loads(json_str)
                else:
                    # Fallback: try parsing entire content
                    result_data = json.loads(content)

                grounding_result = GroundingCheck(**result_data)

            except Exception as e:
                logger.error(f"Failed to parse grounding validation response: {e}")
                logger.debug(f"Raw response: {llm_response.content}")
                # Create a conservative result
                grounding_result = GroundingCheck(
                    is_grounded=False,
                    confidence=0.5,
                    unsupported_claims=["Failed to parse validation result"],
                    supported_claims=[],
                    reasoning="Validation parsing failed",
                    grounding_score=0.0,
                )

            # Store result
            state["grounding_check"] = grounding_result

            # Log results
            logger.info("✓ Grounding validation complete:")
            logger.info(f"  Is Grounded: {grounding_result.is_grounded}")
            logger.info(f"  Grounding Score: {grounding_result.grounding_score:.2%}")
            logger.info(f"  Confidence: {grounding_result.confidence:.2%}")
            logger.info(f"  Supported Claims: {len(grounding_result.supported_claims)}")
            logger.info(
                f"  Unsupported Claims: {len(grounding_result.unsupported_claims)}"
            )

            if grounding_result.unsupported_claims:
                logger.warning("⚠️ Unsupported claims detected:")
                for claim in grounding_result.unsupported_claims[:3]:  # Show first 3
                    logger.warning(f"  - {claim}")

            # Add warning to state if grounding is poor
            if grounding_result.grounding_score < 0.7:
                warning = (
                    f"⚠️ Low grounding score: {grounding_result.grounding_score:.2%}. "
                    f"Response may contain unsupported information."
                )
                state["errors"].append(warning)
                logger.warning(warning)

            return state

    except Exception as e:
        handle_node_error(state, "grounding_validator", e)
        # Create a failed validation result
        state["grounding_check"] = GroundingCheck(
            is_grounded=False,
            confidence=0.0,
            unsupported_claims=["Validation failed due to error"],
            supported_claims=[],
            reasoning=f"Validation error: {e!s}",
            grounding_score=0.0,
        )
        return state
