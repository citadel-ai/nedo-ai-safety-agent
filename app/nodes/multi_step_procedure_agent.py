"""Multi-Step Procedure Agent - Breaks complex procedures into actionable steps."""

import time
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from app.types import JapanHelpdeskState
from app.utils.observability import observe

# Initialize LLM
llm = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_tokens=4096,  # Increased for detailed multi-step procedures
    location="us-central1",
)


class ProcedureStep(BaseModel):
    """A single step in a multi-step procedure."""

    step_number: int = Field(description="Step number in sequence")
    title: str = Field(description="Short title for this step")
    description: str = Field(description="Detailed description of what to do")
    location: str = Field(
        default="", description="Where to do this (office, online, etc.)"
    )
    required_documents: List[str] = Field(
        default_factory=list, description="Documents needed for this step"
    )
    estimated_time: str = Field(default="", description="How long this step takes")
    deadline: str = Field(default="", description="Any deadline for this step")
    dependencies: List[int] = Field(
        default_factory=list, description="Step numbers that must be completed first"
    )
    tips: List[str] = Field(
        default_factory=list, description="Helpful tips or common mistakes"
    )


class MultiStepProcedure(BaseModel):
    """Complete multi-step procedure breakdown."""

    procedure_name: str = Field(description="Name of the overall procedure")
    is_multi_step: bool = Field(description="Whether this requires multiple steps")
    total_estimated_time: str = Field(description="Total time for all steps")
    steps: List[ProcedureStep] = Field(
        default_factory=list, description="Ordered list of steps"
    )
    important_notes: List[str] = Field(
        default_factory=list, description="Critical information to know"
    )
    common_mistakes: List[str] = Field(
        default_factory=list, description="What people often do wrong"
    )


# Output parser
parser = PydanticOutputParser(pydantic_object=MultiStepProcedure)


PROCEDURE_ANALYSIS_PROMPT = """
You are an expert at breaking down complex administrative procedures in Japan into clear, actionable steps.

**User Query**: "{user_query}"
**User Context**: {user_context}
**Search Results Summary**: {search_summary}

**Your Task**: Analyze if this query involves a multi-step procedure. If yes, break it down into clear, sequential steps.

**Examples of Multi-Step Procedures**:
- Visa renewal (gather docs → apply → wait → receive)
- Getting married (marriage registration → visa change → update residence card → insurance)
- Moving apartments (notify old ward → notify new ward → update bank → update work)
- Opening bank account (choose bank → gather docs → visit branch → activate account)

**Examples of Single-Step**:
- "What documents do I need?" (just informational)
- "Where is the immigration office?" (just location)
- "Can I work part-time?" (yes/no question)

**For Multi-Step Procedures, Include**:
1. **Sequential steps** with clear order
2. **Location** for each step (which office, online, etc.)
3. **Required documents** for each step
4. **Estimated time** for each step
5. **Dependencies** (which steps must be done first)
6. **Deadlines** if any exist
7. **Tips** to avoid common mistakes

**Important Guidelines**:
- Be specific about Japanese context (ward offices, immigration offices, etc.)
- Include timing constraints (14-day deadlines, 3-month windows, etc.)
- Mention if steps can be done in parallel
- Note if online alternatives exist
- Include location-specific info when available from context

{format_instructions}
"""


@observe(name="multi_step_procedure_agent")
async def multi_step_procedure_agent_node(
    state: JapanHelpdeskState,
) -> JapanHelpdeskState:
    """
    Analyzes if a query requires multi-step procedures and breaks them down.
    Enhances the response with actionable step-by-step guidance.
    """

    import logging

    logger = logging.getLogger(__name__)

    start_time = time.time()

    try:
        # Get user query - use main_request from intake if available to avoid using quick-reply answers
        intake = state.get("intake_session")
        user_query = state["user_input"]

        # Prefer the original main request over the latest user input (which might be a quick-reply answer)
        if intake and hasattr(intake, "collected_info") and intake.collected_info:
            main_request = intake.collected_info.get("main_request")
            if main_request:
                user_query = main_request
                logger.info(
                    f"📋 Using original main_request: '{main_request}' instead of latest input: '{state['user_input']}'"
                )

        # Build context
        context = {}
        if intake:
            if hasattr(intake, "visa_type") and intake.visa_type:
                context["visa_type"] = intake.visa_type
            if hasattr(intake, "user_location") and intake.user_location:
                context["location"] = intake.user_location
            if hasattr(intake, "timeline") and intake.timeline:
                context["timeline"] = intake.timeline

        # Get search results summary
        search_summary = "No search results available"
        if state.get("hybrid_results"):
            search_summary = state["hybrid_results"].merged_summary
        elif state.get("_raw_vector_results") or state.get("_raw_google_results"):
            vector_count = len(state.get("_raw_vector_results", []))
            google_count = len(state.get("_raw_google_results", []))
            search_summary = (
                f"Found {vector_count} vector results and {google_count} Google results"
            )

        logger.info(f"📋 MULTI-STEP PROCEDURE - Analyzing: '{user_query}'")
        logger.info(f"📋 Context: {context}")
        logger.info(f"📋 Search summary received: {search_summary}")

        # DEBUG: Show what raw data is available
        logger.info(f"📋 ===== MULTI-STEP PROCEDURE INPUT DEBUG =====")

        if state.get("_raw_vector_results"):
            logger.info(
                f"📋 Available vector results: {len(state['_raw_vector_results'])}"
            )
            for i, res in enumerate(state["_raw_vector_results"][:2], 1):
                logger.info(f"   Vector {i} type: {type(res).__name__}")
                if hasattr(res, "content"):
                    content = res.content() if callable(res.content) else res.content
                    logger.info(f"   Vector {i} content: {str(content)[:150]}...")
                else:
                    logger.info(f"   Vector {i}: {str(res)[:150]}...")
        else:
            logger.warning(f"📋 ⚠️ No _raw_vector_results in state!")

        if state.get("_raw_google_results"):
            logger.info(
                f"📋 Available Google results: {len(state['_raw_google_results'])}"
            )
            for i, res in enumerate(state["_raw_google_results"][:2], 1):
                logger.info(f"   Google {i} type: {type(res).__name__}")
                if isinstance(res, str):
                    # Show first 300 chars to see if content is included
                    logger.info(f"   Google {i} string content (first 300 chars):")
                    logger.info(f"   {res[:300]}")
                    if "Content:" in res:
                        logger.info(f"   ✅ Has content embedded in string")
                    elif "Snippet:" in res:
                        logger.info(f"   ⚠️ Has snippet but no full content")
                    else:
                        logger.info(f"   ❌ No content or snippet found")
                elif hasattr(res, "title"):
                    title = res.title() if callable(res.title) else res.title
                    logger.info(f"   Google {i} title: {title}")
                    content_attr = getattr(res, "content", None)
                    if content_attr:
                        content = (
                            content_attr() if callable(content_attr) else content_attr
                        )
                        logger.info(
                            f"   Google {i} content preview: {str(content)[:150]}..."
                        )
                    else:
                        logger.info(f"   Google {i} no content attribute")
                else:
                    logger.info(f"   Google {i}: {str(res)[:150]}...")
        else:
            logger.warning(f"📋 ⚠️ No _raw_google_results in state!")

        logger.info(f"📋 =============================================")

        # Create prompt
        format_instructions = parser.get_format_instructions()
        prompt = PROCEDURE_ANALYSIS_PROMPT.format(
            user_query=user_query,
            user_context=context if context else "No specific context",
            search_summary=search_summary,
            format_instructions=format_instructions,
        )

        messages = [
            SystemMessage(
                content="You are an expert at analyzing administrative procedures."
            ),
            HumanMessage(content=prompt),
        ]

        # Get LLM response
        response = await llm.ainvoke(messages)

        logger.info(f"📋 MULTI-STEP PROCEDURE - Parsing LLM response")
        procedure = parser.parse(response.content)

        if procedure.is_multi_step and procedure.steps:
            logger.info(
                f"✅ MULTI-STEP PROCEDURE DETECTED: '{procedure.procedure_name}'"
            )
            logger.info(f"   Total steps: {len(procedure.steps)}")
            logger.info(f"   Estimated time: {procedure.total_estimated_time}")

            # Format procedure into recommendations
            recommendations = []
            recommendations.append(
                f"**{procedure.procedure_name}** (Est. time: {procedure.total_estimated_time})"
            )
            recommendations.append("")

            for step in procedure.steps:
                step_text = f"**Step {step.step_number}: {step.title}**"
                recommendations.append(step_text)
                recommendations.append(f"→ {step.description}")

                if step.location:
                    recommendations.append(f"📍 Where: {step.location}")
                if step.required_documents:
                    recommendations.append(
                        f"📄 Documents: {', '.join(step.required_documents)}"
                    )
                if step.estimated_time:
                    recommendations.append(f"⏱️ Time: {step.estimated_time}")
                if step.deadline:
                    recommendations.append(f"⚠️ Deadline: {step.deadline}")
                if step.tips:
                    for tip in step.tips:
                        recommendations.append(f"💡 Tip: {tip}")
                recommendations.append("")

            if procedure.important_notes:
                recommendations.append("**⚠️ Important Notes:**")
                for note in procedure.important_notes:
                    recommendations.append(f"• {note}")
                recommendations.append("")

            if procedure.common_mistakes:
                recommendations.append("**🚨 Common Mistakes to Avoid:**")
                for mistake in procedure.common_mistakes:
                    recommendations.append(f"• {mistake}")

            # Add to state recommendations
            if "recommendations" not in state:
                state["recommendations"] = []
            state["recommendations"].extend(recommendations)

            # Store structured procedure
            state["_procedure_breakdown"] = procedure

            logger.info(f"📋 Added {len(procedure.steps)} steps to recommendations")
            logger.info(f"📋 FORMATTED OUTPUT PREVIEW:")
            for line in recommendations[:10]:  # Show first 10 lines
                logger.info(f"   {line}")

        else:
            logger.info(f"ℹ️ Single-step query - no procedure breakdown needed")

        # Update metadata
        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())
        state["completed_steps"].append("multi_step_procedure")

        logger.info(
            f"⏱️ Multi-step procedure analysis completed in {processing_time:.2f}s"
        )

        return state

    except Exception as e:
        logger.error(f"🔴 MULTI-STEP PROCEDURE ERROR: {e}", exc_info=True)
        state["errors"].append(f"Multi-step procedure analysis failed: {str(e)}")
        # Not critical, continue workflow
        return state
