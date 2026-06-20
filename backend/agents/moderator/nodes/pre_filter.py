import logging
import asyncio
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..services import ai_service
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status

logger = logging.getLogger("moderation_pipeline")


@measure_latency("pre_filter")
async def pre_filter_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "pre_filter"})
    data = state.get("input_data") or {}
    title = data.get("title", "")
    description = data.get("description", "")
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    try:
        # Concurrent execution: UI status update + LLM safety check
        _, service_result = await asyncio.gather(
            emit_status(
                thread_id,
                "pre_filter",
                "CHECKING_SAFETY",
                "checking_safety",
                "Analizando seguridad de contenido..."
            ),
            ai_service.analyze_safety(title, description),
            return_exceptions=False
        )
        
        result_data = service_result.get("data", {})
        usage = service_result.get("usage", {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"})
        
        if result_data.get("is_critical"):
            return {
                "early_blocked": True,
                "routing_reason": "early_block",
                "violation_category": "Critical",
                "final_action": "Block",
                "risk_score": 1.0,
                "reasoning": f"Bloqueo automático: {result_data.get('reason', 'Contenido prohibido')}",
                "execution_metrics": {"nodes": {"pre_filter": usage}}
            }
 
        return {"early_blocked": False, "routing_reason": None, "execution_metrics": {"nodes": {"pre_filter": usage}}}
    except Exception as e:
        logger.error(f"Error in pre_filter safety check: {e}")
        usage = {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "error"}

    return {"early_blocked": False, "routing_reason": None, "execution_metrics": {"nodes": {"pre_filter": usage}}}
