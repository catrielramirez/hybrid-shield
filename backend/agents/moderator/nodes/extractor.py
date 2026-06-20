import json
import logging
import asyncio
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..services import ai_service, firestore_service
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status
from ..shared.audit import make_audit_entry, node_metrics
from ..shared.json_utils import clean_json_string

logger = logging.getLogger("moderation_pipeline")


@measure_latency("extractor")
async def feature_extractor_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "extractor"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    data = state.get("input_data") or {}
    gcs_uri = state.get("gcs_uri")

    if not gcs_uri:
        error_msg = "Missing GCS URI in state"
        logger.error(error_msg)
        return {
            "features": {"error": "missing_gcs_uri"},
            "signals": {"image_not_found": True},
            "image_quality_score": 0.0,
            "routing_reason": "extraction_failed",
            "risk_score": 0.5,
            "extraction_failed": True,
            "min_market_price": 0.0,
            "max_market_price": float('inf'),
            "audit_log": [make_audit_entry(
                node="extractor",
                status="error",
                summary=error_msg,
                data={"error": "missing_gcs_uri"}
            )],
            **node_metrics("extractor", prompt_tokens=0, candidates_tokens=0, model_name="none")
        }

    try:
        # Concurrent execution: UI status update + LLM multimodal extraction
        _, service_result = await asyncio.gather(
            emit_status(
                thread_id,
                "extractor",
                "ANALYZING_IMAGE",
                "analyzing_data",
                "Extrayendo características multimodales..."
            ),
            ai_service.extract_multimodal_features(gcs_uri, data),
            return_exceptions=False
        )
        
        raw_features = service_result.get("data", {})
        usage = service_result.get("usage", {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"})

        if isinstance(raw_features, str):
            try:
                features = json.loads(clean_json_string(raw_features))
            except Exception as parse_err:
                logger.error(f"Fallo de parsing tras limpieza: {parse_err}")
                features = {"error": "parsing_failed", "raw_content": raw_features}
        else:
            features = raw_features

        if "error" in features or features.get("error") == "parsing_failed":
            error_msg = f"Gemini extraction/parsing failed: {features.get('error')}"
            return {
                "features": features,
                "signals": {"parsing_error": True},
                "image_quality_score": 0.0,
                "routing_reason": "extraction_failed",
                "risk_score": 0.5,
                "extraction_failed": True,
                "min_market_price": 0.0,
                "max_market_price": float('inf'),
                "audit_log": [make_audit_entry(
                    node="extractor",
                    status="error",
                    summary=error_msg,
                    data=features
                )],
                "execution_metrics": {"nodes": {"extractor": usage}}
            }

        visual_dissonance = features.get("visual_dissonance", False)
        contact_info = features.get("contact_info_detected", False)

        object_category = features.get("object_category", "").strip()
        category_key = object_category.lower().replace(" ", "_") if object_category else "unknown"

        min_market_price = 0.0
        max_market_price = float('inf')

        if category_key != "unknown":
            try:
                price_data = await firestore_service.get_price_thresholds(category_key)
                if price_data:
                    min_market_price = float(price_data["min_price"])
                    max_market_price = float(price_data["max_price"])
                    logger.info(f"Price thresholds retrieved in extractor for '{category_key}': min={min_market_price}, max={max_market_price}")
                else:
                    logger.info(f"No price thresholds found in extractor for '{category_key}'. Using defaults.")
            except Exception as e:
                logger.error(f"Error retrieving price thresholds in extractor for '{category_key}': {e}")
        else:
            logger.info("Category is 'unknown' in extractor. Skipping price threshold lookup.")

        summary = (
            f"Evidence generated. Category: '{features.get('object_category')}'. "
            f"Sellable: {features.get('is_sellable')}. Dissonance: {visual_dissonance}. "
            f"Contact info: {contact_info}. Price bounds: [{min_market_price}, {max_market_price}] ARS."
        )

        try:
            confidence = float(features.get("confidence", 1.0))
        except (ValueError, TypeError):
            confidence = 1.0

        routing_reason = None
        if features.get("image_quality") == "ambiguous":
            routing_reason = "unverifiable_image"
        elif confidence < 0.60:
            routing_reason = "low_confidence"

        return {
            "features": features,
            "extraction_failed": False,
            "min_market_price": min_market_price,
            "max_market_price": max_market_price,
            "signals": {"visual_dissonance": visual_dissonance},
            "image_quality_score": features.get("image_quality_score", 0.0),
            "routing_reason": routing_reason,
            "risk_score": 0.0,
            "audit_log": [make_audit_entry(
                node="extractor",
                status="completed",
                summary=summary,
                data=features,
                evidence={"image_analysis": features}
            )],
            "execution_metrics": {"nodes": {"extractor": usage}}
        }

    except Exception as e:
        error_msg = f"Gemini multimodal analysis failed: {e}"
        logger.error(error_msg)
        usage = {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "error"}
        return {
            "features": {"error": "extraction_failed", "confidence": 0.0},
            "min_market_price": 0.0,
            "max_market_price": float('inf'),
            "signals": {},
            "image_quality_score": 0.0,
            "routing_reason": "extraction_failed",
            "risk_score": 0.5,
            "extraction_failed": True,
            "audit_log": [make_audit_entry(
                node="extractor",
                status="error",
                summary=error_msg,
                data={"error": "extraction_failed"}
            )],
            "execution_metrics": {"nodes": {"extractor": usage}}
        }
