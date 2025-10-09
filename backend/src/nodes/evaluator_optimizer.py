"""
Evaluator-Optimizer Node - Implements Anthropic's evaluator-optimizer pattern.

This node evaluates response quality and iteratively improves responses
following: https://www.anthropic.com/engineering/building-effective-agents
"""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field

from src.core.models import JapanHelpdeskState
from src.core.settings import load_settings
from src.utils.observability import observe

# Initialize settings
settings = load_settings()

# Initialize LLMs
evaluator_llm = ChatVertexAI(
    model=settings.agent_model,
    temperature=settings.agent_temperature,
    max_tokens=1024,
    location=settings.vertex_ai_location,
)

optimizer_llm = ChatVertexAI(
    model=settings.agent_model,
    temperature=settings.agent_temperature,
    max_tokens=2048,
    location=settings.vertex_ai_location,
)

class ResponseEvaluation(BaseModel):
    """Evaluation of a response's quality and completeness."""

    overall_score: float = Field(description="Overall quality score (0-1)")
    completeness_score: float = Field(description="How complete the response is (0-1)")
    accuracy_score: float = Field(
        description="How accurate the information appears (0-1)"
    )
    helpfulness_score: float = Field(
        description="How helpful for the user's situation (0-1)"
    )

    strengths: list[str] = Field(description="What the response does well")
    weaknesses: list[str] = Field(description="Areas that need improvement")
    missing_elements: list[str] = Field(
        description="Important information that's missing"
    )

    needs_improvement: bool = Field(
        description="Whether the response needs to be improved"
    )
    specific_feedback: str = Field(description="Specific feedback for improvement")

    # Japan-specific evaluation criteria
    location_specific: bool = Field(
        description="Whether response is location-specific when needed"
    )
    culturally_appropriate: bool = Field(
        description="Whether response is culturally appropriate"
    )
    practical_actionable: bool = Field(
        description="Whether response provides actionable steps"
    )


EVALUATOR_PROMPT = """
You are an expert evaluator for a Japan helpdesk system. Your role is to critically assess response quality and identify areas for improvement.

🎯 EVALUATION CRITERIA:

COMPLETENESS (25%):
- Does the response fully address the user's question?
- Are all important aspects covered?
- Is context-specific information included (location, visa type, etc.)?

ACCURACY (25%):
- Is the information factually correct?
- Are procedures and requirements accurate?
- Are contact details and office information current?

HELPFULNESS (25%):
- Does it provide actionable next steps?
- Is it tailored to the user's specific situation?
- Does it anticipate follow-up needs?

CULTURAL APPROPRIATENESS (25%):
- Is the tone appropriate for Japan context?
- Does it consider cultural nuances?
- Are Japanese language elements handled correctly?

📊 USER CONTEXT:
Original Query: "{user_query}"
User Location: {user_location}
Visa Type: {visa_type}
Timeline: {timeline}
Urgency: {urgency}

📝 RESPONSE TO EVALUATE:
{response_to_evaluate}

🔍 SOURCES USED:
{sources_used}

{format_instructions}

Provide a thorough evaluation focusing on what would make this response MORE helpful for this specific user's situation.
"""

OPTIMIZER_PROMPT = """
You are a response optimizer for a Japan helpdesk system. Your role is to improve responses based on evaluation feedback.

📊 ORIGINAL RESPONSE:
{original_response}

🔍 EVALUATION FEEDBACK:
Overall Score: {overall_score}/1.0
Specific Issues: {specific_feedback}
Weaknesses: {weaknesses}
Missing Elements: {missing_elements}

📋 USER CONTEXT:
Query: "{user_query}"
Location: {user_location}
Visa Type: {visa_type}
Timeline: {timeline}
Urgency: {urgency}

🎯 OPTIMIZATION GUIDELINES:

1. ADDRESS SPECIFIC FEEDBACK:
   - Fix identified weaknesses
   - Add missing elements
   - Improve unclear sections

2. ENHANCE PERSONALIZATION:
   - Make it more location-specific
   - Tailor to visa type if relevant
   - Consider timeline/urgency

3. IMPROVE ACTIONABILITY:
   - Add specific next steps
   - Include contact information
   - Provide clear procedures

4. MAINTAIN QUALITY:
   - Keep accurate information
   - Preserve helpful elements
   - Ensure cultural appropriateness

Create an improved version of the response that addresses the evaluation feedback while maintaining all the good aspects of the original.
"""

evaluation_parser = PydanticOutputParser(pydantic_object=ResponseEvaluation)


@observe(name="response_evaluator")
async def evaluate_response(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Evaluate the quality of the current response."""
    start_time = time.time()

    try:
        # Get response to evaluate
        response_to_evaluate = state.get("final_response", "")
        if not response_to_evaluate:
            return state

        # Extract user context
        intake_session = state.get("intake_session", {})
        user_context = {
            "user_query": state.get("user_input", ""),
            "user_location": getattr(intake_session, "user_location", None)
            if intake_session
            else None,
            "visa_type": getattr(intake_session, "visa_type", None)
            if intake_session
            else None,
            "timeline": getattr(intake_session, "timeline", None)
            if intake_session
            else None,
            "urgency": getattr(intake_session, "urgency_level", None)
            if intake_session
            else None,
        }

        # Prepare evaluation prompt
        format_instructions = evaluation_parser.get_format_instructions()
        prompt = EVALUATOR_PROMPT.format(
            user_query=user_context["user_query"],
            user_location=user_context["user_location"] or "Not specified",
            visa_type=user_context["visa_type"] or "Not specified",
            timeline=user_context["timeline"] or "Not specified",
            urgency=user_context["urgency"] or "Not specified",
            response_to_evaluate=response_to_evaluate,
            sources_used=state.get("sources", []),
            format_instructions=format_instructions,
        )

        # Get evaluation
        messages = [
            SystemMessage(content="You are an expert response evaluator."),
            HumanMessage(content=prompt),
        ]

        response = await evaluator_llm.ainvoke(messages)
        evaluation: ResponseEvaluation = evaluation_parser.parse(response.content)

        # Store evaluation in state
        state["response_evaluation"] = evaluation
        state["agent_reasoning"].append(
            f"Response evaluated - Score: {evaluation.overall_score:.2f}"
        )

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time

        return state

    except Exception as e:
        state["errors"].append(f"Response evaluation failed: {e!s}")
        return state


@observe(name="response_optimizer")
async def optimize_response(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Optimize the response based on evaluation feedback."""
    start_time = time.time()

    try:
        # Get evaluation
        evaluation = state.get("response_evaluation")
        if not evaluation or not evaluation.needs_improvement:
            return state

        original_response = state.get("final_response", "")
        if not original_response:
            return state

        # Extract user context
        intake_session = state.get("intake_session", {})
        user_context = {
            "user_query": state.get("user_input", ""),
            "user_location": getattr(intake_session, "user_location", None)
            if intake_session
            else None,
            "visa_type": getattr(intake_session, "visa_type", None)
            if intake_session
            else None,
            "timeline": getattr(intake_session, "timeline", None)
            if intake_session
            else None,
            "urgency": getattr(intake_session, "urgency_level", None)
            if intake_session
            else None,
        }

        # Prepare optimization prompt
        prompt = OPTIMIZER_PROMPT.format(
            original_response=original_response,
            overall_score=evaluation.overall_score,
            specific_feedback=evaluation.specific_feedback,
            weaknesses=", ".join(evaluation.weaknesses),
            missing_elements=", ".join(evaluation.missing_elements),
            user_query=user_context["user_query"],
            user_location=user_context["user_location"] or "Not specified",
            visa_type=user_context["visa_type"] or "Not specified",
            timeline=user_context["timeline"] or "Not specified",
            urgency=user_context["urgency"] or "Not specified",
        )

        # Generate optimized response
        messages = [
            SystemMessage(
                content="You are a response optimizer focused on helpfulness and accuracy."
            ),
            HumanMessage(content=prompt),
        ]

        response = await optimizer_llm.ainvoke(messages)
        optimized_response = response.content

        # Update state with optimized response
        state["final_response"] = optimized_response
        state["agent_reasoning"].append(
            "Response optimized based on evaluation feedback"
        )

        # Increase confidence score if optimization was successful
        if evaluation.overall_score < 0.8:
            state["confidence_score"] = min(
                1.0, state.get("confidence_score", 0.0) + 0.2
            )

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time

        return state

    except Exception as e:
        state["errors"].append(f"Response optimization failed: {e!s}")
        return state


@observe(name="evaluator_optimizer")
async def evaluator_optimizer_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Main evaluator-optimizer node implementing Anthropic's pattern."""

    # Initialize evaluation fields if not present
    if "response_evaluation" not in state:
        state["response_evaluation"] = None

    # Only run if we have a response to evaluate
    if not state.get("final_response"):
        return state

    # Evaluate current response
    state = await evaluate_response(state)

    # Optimize if needed (and we haven't already optimized multiple times)
    optimization_count = state.get("optimization_count", 0)
    if (
        state.get("response_evaluation")
        and state["response_evaluation"].needs_improvement
        and optimization_count < 2
    ):  # Limit to 2 optimization rounds
        state = await optimize_response(state)
        state["optimization_count"] = optimization_count + 1

    return state
