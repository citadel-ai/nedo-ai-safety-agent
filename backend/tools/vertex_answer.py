"""
Vertex AI Search Answer tool with session support for multi-turn conversations.
"""

from typing import Any, Optional
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from google.cloud import discoveryengine_v1
from pydantic import Field

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


# Same prompt as current implementation
ANSWER_PROMPT = """You are a helpful assistant specialized in Japanese official procedures.

**FORMATTING REQUIREMENTS:**
- Only reply in English
- Use **bold** and _italics_ to highlight the most important information (key requirements, deadlines, critical documents)
- Add blank lines between different sections for better readability
- Use headings (##) for major sections when appropriate
- Keep paragraphs short (2-3 sentences max)

**CONTENT GUIDELINES:**
When answering:
1. **Start with the most important information** - what the person MUST know or do first
3. **Highlight critical requirements** - use bold for:
   - Required documents (e.g., **在留カード required**)
   - Important deadlines (e.g., **Must apply within 30 days**)
   - Key fees or costs
   - Office locations or contact info
4. **Organize related information** - use bullet lists for non-sequential items
5. **Add context when helpful** - mention Japanese terms in parentheses
7. **Acknowledge uncertainty** - if information is incomplete or may vary

Focus on accuracy and practical guidance for people navigating Japanese administrative processes."""


class VertexAIAnswerTool(BaseTool):
    """
    Vertex AI Search Answer tool with session support.
    
    LangGraph pattern: Extract thread_id from RunnableConfig
    Maps thread_id to Vertex AI Search session for multi-turn conversations.
    """
    name: str = "vertex_answer_search"
    description: str = "Search for information about Japanese official procedures with multi-turn conversation support"
    
    # Config
    project_id: str = Field(default_factory=lambda: Config.GOOGLE_CLOUD_PROJECT)
    engine_id: str = Field(default_factory=lambda: Config.VERTEX_AI_SEARCH_ENGINE_ID)  # Can be engine or data store ID
    location_id: str = "global"
    serving_config_id: str = "default_serving_config"  # Changed to match official example
    
    # Private client (initialized on first use)
    _client: Optional[discoveryengine_v1.ConversationalSearchServiceClient] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _get_client(self) -> discoveryengine_v1.ConversationalSearchServiceClient:
        """Lazy initialization of the client."""
        if self._client is None:
            self._client = discoveryengine_v1.ConversationalSearchServiceClient()
        return self._client
    
    def _build_serving_config_name(self) -> str:
        """
        Build the serving config resource name.
        
        Uses engines path (not dataStores) as per official answer method docs.
        """
        return (
            f"projects/{self.project_id}/locations/{self.location_id}/"
            f"collections/default_collection/engines/{self.engine_id}/"
            f"servingConfigs/{self.serving_config_id}"
        )
    
    def _build_session_name(self, session_id: str = None) -> str:
        """
        Build session resource name.
        
        Uses engines path (not dataStores) as per official answer method docs.
        
        Args:
            session_id: Existing session ID, or None to use wildcard for auto-creation
        
        Returns:
            Session resource name
        """
        # Use wildcard "-" for auto-creation, or specific session ID
        sid = session_id if session_id else "-"
        return (
            f"projects/{self.project_id}/locations/{self.location_id}/"
            f"collections/default_collection/engines/{self.engine_id}/"
            f"sessions/{sid}"
        )
    
    def _run(self, query: str, run_manager=None, **kwargs) -> Any:
        """
        Execute answer query with session support.
        
        Thread ID extracted from config automatically by LangGraph.
        
        Args:
            query: The search query
            **kwargs: Additional arguments including 'config' and 'session_id'
            
        Returns:
            AnswerQueryResponse with answer and citations
        """
        # Get config from kwargs (passed by LangGraph)
        config: RunnableConfig = kwargs.get("config", {})
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        
        # Get existing session ID (if any) from kwargs
        existing_session_id = kwargs.get("session_id")
        
        logger.info(f"🔍 Answer query for thread_id: {thread_id}")
        logger.info(f"📝 Query: {query[:100]}...")
        
        # Get client
        client = self._get_client()
        
        # Build resource names
        serving_config = self._build_serving_config_name()
        
        # Build session name - use existing session or create new one
        session = self._build_session_name(existing_session_id)
        
        if existing_session_id:
            logger.info(f"📍 Using existing session: {existing_session_id}")
        else:
            logger.info(f"📍 Creating new session (auto-assign)")
        
        # Build answer query request WITH session support (matching official example)
        request = discoveryengine_v1.AnswerQueryRequest(
            serving_config=serving_config,
            query=discoveryengine_v1.Query(text=query),
            session=session,  # ✅ Enable multi-turn with sessions
            
            # Query understanding spec (from official example) - improves multi-turn
            query_understanding_spec=discoveryengine_v1.AnswerQueryRequest.QueryUnderstandingSpec(
                query_rephraser_spec=discoveryengine_v1.AnswerQueryRequest.QueryUnderstandingSpec.QueryRephraserSpec(
                    disable=False,  # Enable query rephrasing for follow-ups
                    max_rephrase_steps=1,
                ),
                query_classification_spec=discoveryengine_v1.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec(
                    types=[
                        discoveryengine_v1.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.ADVERSARIAL_QUERY,
                        discoveryengine_v1.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.NON_ANSWER_SEEKING_QUERY,
                    ]
                ),
            ),
            
            # Answer generation specification (matching official example)
            answer_generation_spec=discoveryengine_v1.AnswerQueryRequest.AnswerGenerationSpec(
                model_spec=discoveryengine_v1.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                    model_version="gemini-2.0-flash-001/answer_gen/v1",  # Latest stable version
                ),
                prompt_spec=discoveryengine_v1.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                    preamble=ANSWER_PROMPT,
                ),
                include_citations=True,
                ignore_adversarial_query=False,  # Handled by query classification instead
                ignore_non_answer_seeking_query=False,  # Handled by query classification instead
                ignore_jail_breaking_query=True,
                ignore_low_relevant_content=False,  # Let model decide
                answer_language_code="en",
            ),
            
            # Search specification
            search_spec=discoveryengine_v1.AnswerQueryRequest.SearchSpec(
                search_params=discoveryengine_v1.AnswerQueryRequest.SearchSpec.SearchParams(
                    max_return_results=5,  # Similar to summary_result_count
                ),
            ),
            
            # User tracking (from official example)
            user_pseudo_id=f"thread-{thread_id}",  # Track by thread for analytics
        )
        
        try:
            # Call answer method
            logger.info("🌐 Calling Vertex AI Answer method...")
            response = client.answer_query(request)
            
            logger.info(f"✅ Got answer response: ")
            logger.info(response)
            if hasattr(response, 'answer') and response.answer:
                logger.info(f"📄 Answer text length: {len(response.answer.answer_text)} chars")
                if hasattr(response.answer, 'citations'):
                    logger.info(f"📚 Citations count: {len(response.answer.citations)}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error calling answer_query: {str(e)}")
            raise


def create_vertex_answer_tool() -> VertexAIAnswerTool:
    """Create and configure the Vertex AI Answer Tool."""
    return VertexAIAnswerTool()


# Initialize tool once at module level
vertex_answer_tool = create_vertex_answer_tool()

