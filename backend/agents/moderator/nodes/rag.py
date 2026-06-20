import logging
import asyncio
import traceback
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..services import firestore_service, rag_service
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status
from ..shared.audit import make_audit_entry


logger = logging.getLogger("moderation_pipeline")


@measure_latency("rag")
async def rag_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "rag"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    try:
        features = state.get("features") or {}
        # PHASE 1: Policy Search
        obj_name = features.get('primary_object') or features.get('primary_object_in_image') or "unknown"
        query = f"Politicas e-commerce sobre {obj_name} y links de contacto o disonancia visual"

        try:
            # Concurrent execution: UI status update + policy search
            _, (rag_context, policy_citations) = await asyncio.gather(
                emit_status(
                    thread_id,
                    "rag",
                    "SEARCHING_POLICIES",
                    "reading_doc",
                    "Buscando políticas aplicables..."
                ),
                rag_service.search_policies(query),
                return_exceptions=False
            )
        except Exception as e:
            logger.error(f"RAG service failed: {e}", exc_info=True)
            rag_context = "No se pudo recuperar contexto de políticas. Error técnico."
            policy_citations = []
            # Ensure simple status update executes even if RAG fails
            try:
                await emit_status(
                    thread_id,
                    "rag",
                    "SEARCHING_POLICIES",
                    "reading_doc",
                    "Buscando políticas aplicables..."
                )
            except Exception as status_err:
                logger.error(f"Status update also failed: {status_err}", exc_info=True)

        usage = {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}

        # PHASE 3: Return Updated State
        return {
            "rag_context": rag_context,
            "policy_citations": policy_citations,
            "audit_log": [make_audit_entry(
                node="rag", 
                status="completed",
                summary=f"Retrieved {len(policy_citations)} policy citations for object '{obj_name}'.",
                data={
                    "query": query, 
                    "policy_matches": policy_citations
                },
                evidence={"snippets": [c.get("snippet", "") for c in policy_citations if isinstance(c, dict)]}
            )],
            "execution_metrics": {"nodes": {"rag": usage}}
        }
    except Exception as e:
        error_msg = f"Critical failure in RAG node: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"[NODE_ERROR] Node 'rag' failed with critical error: {e}", flush=True)
        
        # Inline status update (Pattern B - custom payload/swallows exceptions)
        try:
            await firestore_service.update_job_status(
                thread_id, 
                "FAILED", 
                {
                    "error_message": error_msg,
                    "metadata": {
                        "error": error_msg,
                        "traceback": traceback.format_exc()
                    }
                }
            )
            await firestore_service.update_ui_state(
                thread_id,
                current_node="rag",
                ui_context="error",
                ui_message=f"Error crítico en RAG: {str(e)}",
                status="FAILED"
            )
        except Exception as fe:
            logger.error(f"Failed to update Firestore status on RAG critical error for thread {thread_id}: {fe}", exc_info=True)
            
        return {
            "status": "FAILED",
            "early_blocked": True,
            "requires_human_intervention": False,
            "final_action": "Block",
            "audit_log": [make_audit_entry(
                node="rag", 
                status="failed",
                summary=error_msg,
                data={"error": str(e), "traceback": traceback.format_exc()}
            )]
        }
