import json
import logging
import asyncio
from google.cloud import bigquery
from langchain_core.runnables import RunnableConfig
import config
from ..state import AgentState
from ..shared.observability import measure_latency
from ..shared.audit import make_audit_entry

logger = logging.getLogger("moderation_pipeline")


@measure_latency("fly_wheel")
async def data_flywheel_node(state: AgentState, config: RunnableConfig): 
    logger.info("node_started", extra={"node": "fly_wheel"})
    
    current_action = state.get("final_action")
    human_feedback = state.get("human_feedback")
    if isinstance(human_feedback, dict):
        current_action = human_feedback.get("decision", current_action)

    def _safe_float(value, default=None):
        try:
            f = float(value) if value is not None else default
            if f is None or f != f or f == float('inf') or f == float('-inf'):
                return default
            return f
        except (TypeError, ValueError):
            return default

    try:
        table_id = f"{config.get_project_id()}.moderation_dataset.evaluations"
        
        input_data = state.get("input_data") or {}
        features = state.get("features") or {}
        execution_metrics = state.get("execution_metrics") or {}
        
        row = {
            # --- Base Traceability ---
            "thread_id": config.get("configurable", {}).get("thread_id") or state.get("thread_id"),
            "product_title": input_data.get("title"),
            "product_description": input_data.get("description"),
            "image_url": state.get("gcs_uri"),
            "risk_score": _safe_float(state.get("risk_score"), default=0.0),
            "final_action": current_action,
            "reasoning": state.get("reasoning"),
            "is_early_blocked": bool(state.get("early_blocked", False)),
            "timestamp": make_audit_entry("fly_wheel", "completed", "dummy")["timestamp"], # Uses timestamp mechanism
            "execution_metrics": json.dumps(execution_metrics),
            
            # --- Enriched fields for Data Flywheel ---
            "object_category": features.get("object_category", "unknown"),
            "dissonance_detected": bool(state.get("signals", {}).get("visual_dissonance", False)),
            "uncertainty": _safe_float(state.get("uncertainty"), default=0.0),
            "min_price": _safe_float(state.get("min_market_price")),
            "max_price": _safe_float(state.get("max_market_price")),
            "policy_violations_count": len(state.get("policy_violations", [])),
            "routing_reason": state.get("routing_reason"),
            "image_quality_score": _safe_float(state.get("image_quality_score"), default=1.0)
        }
        
        def _execute_insert():
            client = bigquery.Client()
            errors = client.insert_rows_json(table_id, [row])
            if errors:
                logger.error(f"BigQuery insertion errors: {errors}")
            
        async def _safe_execute_insert():
            try:
                await asyncio.to_thread(_execute_insert)
            except Exception as e:
                logger.error(f"BigQuery insertion failed: {e}", exc_info=True)
                
        # Synchronously block to guarantee BQ insert happens before node ends
        await _safe_execute_insert()
            
    except Exception as e:
        logger.error(f"Graceful failure in data_flywheel_node BigQuery sink setup: {e}", exc_info=True)
        
    return {
        "audit_log": [make_audit_entry(
            node="fly_wheel",
            status="completed",
            summary=f"Data persisted for thread {state.get('thread_id')}"
        )],
        "final_action": current_action
    }
