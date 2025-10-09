# Copyright 2025 Google LLC

"""Legal advice checker node for LangGraph with Langfuse observability."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from src.core.models import JapanHelpdeskState, LegalAdviceCheck
from src.utils.llm_factory import create_llm
from src.utils.node_helpers import handle_node_error, track_execution
from src.utils.observability import observe

# Initialize LLM and parser
llm = create_llm()
parser = PydanticOutputParser(pydantic_object=LegalAdviceCheck)


def _get_response_content(state: JapanHelpdeskState) -> str:
    """Extract response content from various result types."""
    if state.get("hybrid_results"):
        return state["hybrid_results"].merged_summary
    elif state.get("vector_results"):
        return state["vector_results"].merged_summary
    elif state.get("rag_results"):
        return state["rag_results"].summary
    return ""


@observe(name="legal_checker_node")
async def legal_checker_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Check for unauthorized legal advice in responses."""
    
    try:
        with track_execution(state, "legal_check"):
            response_content = _get_response_content(state)
            
            if not response_content:
                # No content to check, assume compliant
                state["legal_check_result"] = LegalAdviceCheck(
                    contains_legal_advice=False,
                    problematic_phrases=[],
                    suggested_replacements=[],
                    confidence=1.0,
                )
                return state
            
            format_instructions = parser.get_format_instructions()
            prompt = f"""
Check if this response contains unauthorized legal advice.

{format_instructions}

Response to check: "{response_content}"
"""
            
            messages = [
                SystemMessage(content="You are a legal compliance checker."),
                HumanMessage(content=prompt),
            ]
            
            response = await llm.ainvoke(messages)
            result = parser.parse(response.content)
            
            state["legal_check_result"] = result
            state["tokens_used"] = state.get("tokens_used", 0) + len(response.content.split())
        
        return state
        
    except Exception as e:
        # Assume compliant if check fails
        handle_node_error(state, "legal_checker", e)
        state["legal_check_result"] = LegalAdviceCheck(
            contains_legal_advice=False,
            problematic_phrases=[],
            suggested_replacements=[],
            confidence=0.5,
        )
        return state
