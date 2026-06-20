import logging
from langgraph.types import interrupt
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..services import firestore_service
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status
from ..shared.audit import make_audit_entry

logger = logging.getLogger("moderation_pipeline")


@measure_latency("human_in_the_loop")
async def human_review(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "human_in_the_loop"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    # Simple pending update (Pattern A)
    await emit_status(
        thread_id,
        "human_in_the_loop",
        "PENDING_HUMAN_REVIEW",
        "pending_human_review",
        "Esperando revisión humana..."
    )

    # Execution paused until user feedback is received (LangGraph native mechanism)
    decision = interrupt({
        "mensaje": "Revisión requerida",
        "datos": state.get("reasoning", "No reasoning summary provided.")
    })

    feedback = decision if isinstance(decision, dict) else {}
    human_decision = feedback.get("decision")
    human_justification = feedback.get("justification", "Sin justificación proporcionada.")

    if human_decision == "Approve":
        final_action = "Approve"
        status = "APPROVE"
    elif human_decision == "Block":
        final_action = "Block"
        status = "BLOCK"
    else:
        # Resume failsafe return to avoid breaking LangGraph reducers
        return {
            "requires_human_intervention": True,
            "audit_log": [make_audit_entry(
                node="human_in_the_loop",
                status="pending",
                summary="Graph was resumed but no valid human decision was matched."
            )],
            "execution_metrics": {
                "nodes": {
                    "human_in_the_loop": {
                        "prompt_tokens": 0,
                        "candidates_tokens": 0,
                        "model_name": "none"
                    }
                }
            }
        }

    # Final verdict persist logic (Pattern B - inline to handle complex metadata/swallow errors)
    async def safe_final_status_update():
        try:
            input_data = state.get("input_data") or {}
            features = state.get("features") or {}
            await firestore_service.update_job_status(
                thread_id,
                status,
                metadata={
                    "human_reviewed": True,
                    "final_decision": human_decision,
                    "human_justification": human_justification,
                    "product_title": input_data.get("title", ""),
                    "image_url": state.get("gcs_uri", ""),
                    "price": input_data.get("price", 0.0),
                    "risk_score": state.get("risk_score", 0.0),
                    "final_action": final_action,
                    "routing_reason": state.get("routing_reason"),
                    "uncertainty": state.get("uncertainty"),
                    "min_price": state.get("min_market_price"),
                    "max_price": state.get("max_market_price"),
                    "object_category": features.get("primary_object") or features.get("primary_object_in_image"),
                    "signals": state.get("signals"),
                    "policy_violations": state.get("policy_violations"),
                    "reasoning": state.get("reasoning")
                }
            )
            await firestore_service.update_ui_state(
                thread_id,
                current_node="human_in_the_loop",
                ui_context="human_review_completed",
                ui_message=f"Revisión completada: {human_decision}",
                status=status,
                result={"human_reviewed": True, "final_decision": human_decision, "justification": human_justification}
            )
        except Exception as e:
            logger.error(f"Error saving human decision to Firestore: {e}", exc_info=True)

    await safe_final_status_update()

    return {
        "final_action": final_action,
        "human_feedback": feedback,
        "requires_human_intervention": False,
        "audit_log": [make_audit_entry(
            node="human_in_the_loop",
            status="completed",
            summary=f"Human review completed: {human_decision}.",
            data={"decision": human_decision}
        )],
        "execution_metrics": {
            "nodes": {
                "human_in_the_loop": {
                    "prompt_tokens": 0,
                    "candidates_tokens": 0,
                    "model_name": "none"
                }
            }
        }
    }
