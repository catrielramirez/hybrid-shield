import logging
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..constants import RISK_WEIGHTS
from ..services import firestore_service
from ..shared.observability import measure_latency
from ..shared.audit import make_audit_entry

logger = logging.getLogger("moderation_pipeline")


@measure_latency("decision")
async def decision_node(state: AgentState, config: RunnableConfig): 
    logger.info("node_started", extra={"node": "decision"})
    
    features = state.get("features") or {}
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    try:
        confidence = float(features.get("confidence", 1.0))
    except (ValueError, TypeError):
        confidence = 1.0
        
    uncertainty = 1.0 - confidence
    score = float(state.get("risk_score", 0.0))
    
    policy_citations = state.get("policy_citations") or []
    policy_violations = state.get("policy_violations") or []

    # Guard clause: if feature extraction failed, route to human review (HITL)
    if state.get("extraction_failed"):
        summary = "Feature extraction failed. Routing to human review."
        # Pattern C: Critical Firestore updates that raise exceptions if failed
        try:
            input_data = state.get("input_data") or {}
            await firestore_service.update_job_status(
                thread_id,
                "MANUAL_REVIEW",
                metadata={
                    "risk_score": score, 
                    "final_action": "Human Review",
                    "product_title": input_data.get("title", ""),
                    "image_url": state.get("gcs_uri", ""),
                    "price": input_data.get("price", 0.0)
                }
            )
            await firestore_service.update_ui_state(
                thread_id,
                current_node="decision",
                ui_context="error_routing",
                ui_message="Derivando a revisión humana (Error de extracción)...",
                status="MANUAL_REVIEW"
            )
        except Exception as e:
            logger.error(f"Critical error saving final decision to Firestore: {e}", exc_info=True)
            raise e
            
        return {
            "final_action": "Human Review",
            "requires_human_intervention": True,
            "policy_citations": policy_citations,
            "policy_violations": policy_violations,
            "reasoning": summary,
            "risk_score": score,
            "audit_log": [make_audit_entry(
                node="decision",
                status="completed",
                summary=summary,
                data={
                    "risk_score": score,
                    "final_action": "Human Review",
                    "requires_human_intervention": True,
                    "policy_violations": policy_violations,
                    "reason": "extraction_failed"
                },
                evidence={"policy_citations": policy_citations}
            )],
            "execution_metrics": {
                "nodes": {
                    "decision": {
                        "prompt_tokens": 0,
                        "candidates_tokens": 0,
                        "model_name": "none"
                    }
                }
            }
        }

    # Adjust risk_score if there are policy_citations
    if policy_citations:
        global_weights = RISK_WEIGHTS or {}
        policy_match_weight = float(global_weights.get("policy_match", 0.15))
        score = min(score + policy_match_weight, 1.0)

    requires_human_intervention = False

    if score >= 0.85:
        action = "Block"
        final_status = "BLOCK"
        summary = (
            f"Risk score {score:.2f} >= 0.85. "
            f"Confidence={confidence:.2f}. "
            f"Uncertainty={uncertainty:.2f}. "
            f"Action: Block."
        )

    elif score < 0.35:
        action = "Approve"
        final_status = "APPROVE"
        summary = (
            f"Risk score {score:.2f} < 0.35. "
            f"Confidence={confidence:.2f}. "
            f"Uncertainty={uncertainty:.2f}. "
            f"Action: Approve."
        )

    else:
        action = "Human Review"
        final_status = "MANUAL_REVIEW"
        requires_human_intervention = True
        summary = (
            f"Risk score {score:.2f} in [0.35, 0.85). "
            f"Confidence={confidence:.2f}. "
            f"Uncertainty={uncertainty:.2f}. "
            f"Action: Human Review."
        )

    # High uncertainty forces human review (unless it is already a hard Block)
    if uncertainty > 0.75 and action != "Block":
        action = "Human Review"
        final_status = "MANUAL_REVIEW"
        requires_human_intervention = True
        summary = (
            f"Uncertainty {uncertainty:.2f} > 0.75. "
            f"Risk score={score:.2f}. "
            f"Action: Human Review."
        )

    if policy_violations:
        violated_ids = ", ".join(
            str(v.get("policy_id") or "?")
            for v in policy_violations if isinstance(v, dict)
        )
        summary += f" Policies violated: {violated_ids}."

    # Pattern C: Critical Firestore updates that raise exceptions if failed
    try:
        input_data = state.get("input_data") or {}
        features = state.get("features") or {}
        await firestore_service.update_job_status(
            thread_id,
            final_status,
            metadata={
                "risk_score": score,
                "final_action": action,
                "product_title": input_data.get("title", ""),
                "image_url": state.get("gcs_uri", ""),
                "price": input_data.get("price", 0.0),
                "routing_reason": state.get("routing_reason"),
                "uncertainty": uncertainty,
                "min_price": state.get("min_market_price"),
                "max_price": state.get("max_market_price"),
                "object_category": features.get("primary_object") or features.get("primary_object_in_image"),
                "signals": state.get("signals"),
                "policy_violations": policy_violations,
                "reasoning": summary
            }
        )
        await firestore_service.update_ui_state(
            thread_id,
            current_node="decision",
            ui_context="final_decision",
            ui_message=f"Decisión final: {action}",
            status=final_status,
            result={"risk_score": score, "final_action": action}
        )
    except Exception as e:
        logger.error(f"Critical error saving final decision to Firestore: {e}", exc_info=True)
        raise e
        
    routing_reason = state.get("routing_reason")
    if not routing_reason:
        if requires_human_intervention:
            routing_reason = "human_review"
        elif action == "Block":
            routing_reason = "high_risk"
        elif action == "Approve":
            routing_reason = "approved"

    return {
        "final_action": action,
        "requires_human_intervention": requires_human_intervention,
        "policy_citations": policy_citations,
        "policy_violations": policy_violations,
        "uncertainty": uncertainty,
        "routing_reason": routing_reason,
        "reasoning": summary,
        "risk_score": score,
        "audit_log": [make_audit_entry(
            node="decision",
            status="completed",
            summary=summary,
            data={
                "risk_score": score,
                "final_action": action,
                "requires_human_intervention": requires_human_intervention,
                "policy_violations": policy_violations
            },
            evidence={"policy_citations": policy_citations}
        )],
        "execution_metrics": {
            "nodes": {
                "decision": {
                    "prompt_tokens": 0,
                    "candidates_tokens": 0,
                    "model_name": "none"
                }
            }
        }
    }
