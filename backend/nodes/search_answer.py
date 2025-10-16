"""
Search node using Vertex AI Answer method with session support.
"""

from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ..core.state import AgentState
from ..tools.vertex_answer import vertex_answer_tool
from ..utils.citation_extractor import extract_citations_from_answer_response
from ..utils.logging_config import get_logger
from ..utils.langfuse_config import trace_node
from ..evaluation.safety import SafetyEvaluator
from ..evaluation.quality import QualityEvaluator
from ..evaluation.audit import get_audit_logger
from ..evaluation.alerts import get_alert_manager

logger = get_logger(__name__)

# Initialize evaluation components
safety_evaluator = SafetyEvaluator()
quality_evaluator = QualityEvaluator()
audit_logger = get_audit_logger()
alert_manager = get_alert_manager()


@trace_node("search_and_respond_with_answer")
def search_and_respond_with_answer(
    state: AgentState, 
    config: RunnableConfig  # ✅ LangGraph passes this automatically
) -> Dict[str, Any]:  # ✅ Return updates, not full state
    """
    Execute Vertex AI Search using answer method with session support.
    
    LangGraph patterns:
    - Accepts RunnableConfig for thread_id access
    - Returns dict of updates (merged by LangGraph)
    - Keeps logic simple and focused
    
    The answer method automatically handles multi-turn conversation context
    via sessions, which are persisted in the state.
    """
    try:
        # Get latest user query
        query_text = None
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                query_text = message.content
                break
        
        if not query_text:
            return {"error": "No user message found in state"}
        
        # Get existing session ID from state (if any)
        existing_session_id = state.get("vertex_session_id")
        
        # Enhance query with collected facts (same as current implementation)
        collected_facts = state.get("collected_facts", {})
        query = query_text
        
        if collected_facts:
            context_parts = [f"{k}: {v}" for k, v in collected_facts.items() if v]
            if context_parts:
                query = f"{query_text} (Context: {', '.join(context_parts)})"
                logger.info(f"🔧 Enhanced query with context")
        
        logger.info(f"🔍 Answer Query: {query[:100]}...")
        logger.info(f"📋 Collected Facts: {collected_facts}")
        if existing_session_id:
            logger.info(f"🔄 Using existing session: ...{existing_session_id[-8:]}")
        
        # ✅ Call answer tool - pass config AND existing session_id
        raw_response = vertex_answer_tool.invoke(
            query, 
            config=config,
            session_id=existing_session_id  # Pass existing session or None
        )
        
        # Extract answer text (new format)
        answer_text = ""
        if hasattr(raw_response, 'answer') and raw_response.answer:
            answer_text = raw_response.answer.answer_text
        
        if not answer_text:
            logger.warning("⚠️ No answer text in response")
            answer_text = "I couldn't generate an answer. Please try rephrasing your question."
        
        logger.info(f"✅ Got answer ({len(answer_text)} chars)")
        
        # Extract session ID from response (for multi-turn)
        # The session name is in the format: projects/.../sessions/{session_id}
        new_session_id = None
        if hasattr(raw_response, 'session') and raw_response.session:
            session_name = raw_response.session.name
            # Extract just the session ID from the full resource name
            if '/sessions/' in session_name:
                new_session_id = session_name.split('/sessions/')[-1]
                if not existing_session_id:
                    logger.info(f"✨ Created new session: {new_session_id}")
                logger.info(f"💾 Storing session ID for future turns")
        
        # Extract citations (new format for answer response)
        citations = extract_citations_from_answer_response(raw_response)
        logger.info(f"📚 Extracted {len(citations)} citations")
        
        for cit in citations:
            logger.info(f"   [{cit['citation_number']}] {cit['title']}")
            if cit.get('url'):
                logger.info(f"       URL: {cit['url']}")
        
        # ==================== EVALUATION HOOKS ====================
        
        # Get thread_id for logging
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        
        # 1. Safety Evaluation (PII + Content Safety)
        safety_result = safety_evaluator.evaluate(
            text=answer_text,
            citations=citations,
            check_pii=True,
            check_content=True
        )
        
        # Log PII detection if found
        if safety_result.get("pii", {}).get("has_pii"):
            pii_data = safety_result["pii"]
            audit_logger.log_pii_detection(
                thread_id=thread_id,
                pii_types=pii_data["pii_types"],
                risk_level=pii_data["risk_level"],
                location="response"
            )
            
            # Alert if high risk
            if pii_data["risk_level"] in ['medium', 'high']:
                alert_manager.alert_pii_detected(
                    pii_types=pii_data["pii_types"],
                    risk_level=pii_data["risk_level"],
                    location="response",
                    thread_id=thread_id
                )
        
        # Log safety issues
        if not safety_result.get("safety", {}).get("is_safe", True):
            safety_data = safety_result["safety"]
            audit_logger.log_safety_violation(
                thread_id=thread_id,
                violation_type="content_safety",
                details=safety_data
            )
            alert_manager.alert_safety_violation(
                violation_type="content_safety",
                details=safety_data,
                thread_id=thread_id
            )
        
        # 2. Quality Evaluation
        quality_metrics = quality_evaluator.evaluate_response(
            query=query_text,
            response=answer_text,
            citations=citations
        )
        
        # Log quality issues
        if quality_metrics.quality_score < quality_evaluator.quality_threshold:
            audit_logger.log_event(
                event_type=audit_logger.log_event.__self__.__class__.__name__,  # Using a workaround
                thread_id=thread_id,
                details={
                    "event": "low_quality_response",
                    "quality_score": quality_metrics.quality_score,
                    "issues": quality_metrics.issues
                }
            )
            alert_manager.alert_low_quality(
                quality_score=quality_metrics.quality_score,
                issues=quality_metrics.issues,
                thread_id=thread_id
            )
        
        # 3. Task Completion Evaluation
        conversation_length = len(state.get("messages", []))
        task_result = quality_evaluator.evaluate_task_completion(
            query=query_text,
            response=answer_text,
            conversation_length=conversation_length,
            error=None
        )
        
        # 4. Log response to audit
        audit_logger.log_response(
            thread_id=thread_id,
            response=answer_text,
            citations_count=len(citations),
            quality_score=quality_metrics.quality_score
        )
        
        # ✅ Return only updates (LangGraph merges into state)
        state_updates = {
            "messages": [AIMessage(content=answer_text)],
            "answer": answer_text,
            "citations": citations,
            "error": None,
            # Add evaluation results to state
            "quality_score": quality_metrics.quality_score,
            "safety_score": safety_result.get("safety", {}).get("safety_score", 1.0),
            "task_completed": task_result.task_completed,
            "completion_quality": task_result.completion_quality,
            "requires_followup": task_result.requires_followup
        }
        
        # Add session ID if we got one
        if new_session_id:
            state_updates["vertex_session_id"] = new_session_id
        
        return state_updates
        
    except Exception as e:
        error_msg = f"Error calling Vertex AI Answer: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "messages": [AIMessage(content=error_msg)],
            "answer": "",
            "error": error_msg
        }

