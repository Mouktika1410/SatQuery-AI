"""
AI Assistant Chat Endpoint.

Routes natural language queries to the deterministic orchestration service.
The assistant only describes computed results — it never invents metrics.
"""

from fastapi import APIRouter

from app.schemas.chat import ChatQuery, ChatResponse
from app.services.orchestration import AgentOrchestrationService
from app.core.config import settings

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about flood analysis results",
    description=(
        "Natural language query interface for flood analysis results. "
        "The assistant only describes metrics computed by the analysis pipeline. "
        "It never invents geographic statistics or GIS values."
    ),
)
async def query_assistant(payload: ChatQuery) -> ChatResponse:
    """
    Answer natural language questions using computed flood analysis results.
    """
    # Import here to avoid circular dependency
    from app.api.v1.endpoints.flood import _session_cache

    pipeline_result = None
    if payload.session_id and payload.session_id in _session_cache:
        pipeline_result = _session_cache[payload.session_id].get("pipeline_result")

    orchestrator = AgentOrchestrationService(api_key=settings.GEMINI_API_KEY)
    result = orchestrator.answer_query(payload.question, pipeline_result)

    return ChatResponse(**result)
