import logging
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..constants import RISK_WEIGHTS
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status
from ..shared.audit import make_audit_entry
from ..policy_rules import evaluate_policy_rules

logger = logging.getLogger("moderation_pipeline")


@measure_latency("risk_evaluator")
async def risk_evaluator_node(state: AgentState, config: RunnableConfig): 
    logger.info("node_started", extra={"node": "risk_evaluator"})
    
    features = state.get("features") or {}
    data = state.get("input_data") or {}
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    # Simple status update (Pattern A)
    try:
        await emit_status(
            thread_id,
            "risk_evaluator",
            "EVALUATING_RISK",
            "evaluating_risk",
            "Evaluando nivel de riesgo..."
        )
    except Exception as e:
        logger.error(f"Status update failed but continuing with risk evaluation: {e}", exc_info=True)
    
    min_market_price = float(state.get("min_market_price", 0.0))
    max_market_price = float(state.get("max_market_price", float('inf')))
    price = float(data.get("price", 0))
    
    # Call pure policy evaluation function
    signals = evaluate_policy_rules(features, data, min_market_price, max_market_price)
    
    active_signals = [k for k, v in signals.items() if v]
    logic_summary = f"Logic signals: {', '.join(active_signals)}" if active_signals else "No logic violations detected."
    
    # PHASE 2: Risk Aggregation (Weighted Scoring)
    total_weight = 0.0
    risk_breakdown = []
    global_weights = RISK_WEIGHTS or {}

    for signal_name, is_active in signals.items():
        if is_active and signal_name in global_weights:
            weight = global_weights[signal_name]
            total_weight += weight
            risk_breakdown.append({"factor": signal_name, "weight": weight})

    # HARD SAFETY RULE: banned_object siempre produce riesgo máximo
    if signals.get("banned_object"):
        summary = f"{logic_summary} | CRITICAL: Hard safety rule triggered due to banned_object. Maximum risk score assigned."
        return {
            "signals": signals,
            "risk_score": 1.0, 
            "risk_breakdown": [{"factor": "banned_object", "weight": 1.0}], 
            "audit_log": [make_audit_entry(
                node="risk_evaluator",
                status="completed",
                summary=summary,
                data={"risk_score": 1.0, "reason": "banned_object_hard_block", "signals": signals},
                evidence={"signals": signals, "features_used": features, "price": price}
            )],
            "execution_metrics": {"nodes": {"risk_evaluator": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}}}
        }

    # MASCOTAS: animal ambiguo en imagen — suma peso pero no fuerza hard block
    if signals.get("animal_in_image_ambiguous"):
        total_weight += 0.4
        risk_breakdown.append({"factor": "animal_in_image_ambiguous", "weight": 0.4})

    risk_score = min(total_weight, 1.0)
    summary = f"{logic_summary} | Risk score: {risk_score:.2f} (Total weight: {total_weight:.2f})."

    return {
        "signals": signals,
        "risk_score": risk_score, 
        "risk_breakdown": risk_breakdown, 
        "audit_log": [make_audit_entry(
            node="risk_evaluator",
            status="completed",
            summary=summary,
            data={
                "signals": signals,
                "risk_score": risk_score, 
                "total_weight": total_weight,
                "risk_breakdown": risk_breakdown
            },
            evidence={"signals": signals, "weights": global_weights, "features_used": features, "price": price}
        )],
        "execution_metrics": {"nodes": {"risk_evaluator": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}}}
    }
