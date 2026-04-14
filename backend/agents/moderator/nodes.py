import os
import json
import logging
import time
from datetime import datetime, timezone
from vertexai.generative_models import GenerativeModel, Image, Part
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.cloud import bigquery
from .state import AgentState
logger = logging.getLogger("moderation_pipeline")

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("moderation_pipeline")
except ImportError:
    # Fallback to a dummy tracer if opentelemetry is not installed (e.g. in some remote environments)
    import contextlib
    class DummyTracer:
        @contextlib.contextmanager
        def start_as_current_span(self, name, *args, **kwargs):
            yield None
    tracer = DummyTracer()



from typing import Optional

def measure_latency(span_name: Optional[str] = None):
    """Decorator to measure and log node execution time and trace spans."""
    def decorator(func):
        def wrapper(state: AgentState, *args, **kwargs):
            nonlocal span_name
            actual_span_name = span_name
            if actual_span_name is None:
                actual_span_name = func.__name__.replace("_node", "")
                
            with tracer.start_as_current_span(actual_span_name):
                start_time = time.time()
                result = func(state, *args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                
                # Use thread_id or similar as pipeline_id for correlation if available
                pipeline_id = state.get("thread_id", "unknown") 
                
                logger.info(
                    "node_latency",
                    extra={
                        "node": actual_span_name,
                        "latency_ms": latency_ms,
                        "pipeline_id": pipeline_id
                    }
                )
                return result
        return wrapper
    return decorator

from .services import ai_service, firestore_service

# Constants with fallback for remote environment
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
DATA_STORE_ID = os.getenv("DATA_STORE_ID")

# weights
RISK_WEIGHTS = {

    "banned_object": 1.0,
    "external_contact": 1.0,
    "product_unusable": 0.9,
    "visual_dissonance": 0.7,
    "price_anomaly": 0.6,
    "low_quality_image": 0.3,
    "policy_match": 0.4,
}



def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# ================================================================
# Nodo 0: Pre-Filter (Critical Violation Check)
# ================================================================
@measure_latency("pre_filter")
def pre_filter_node(state: AgentState):
    logger.info("node_started", extra={"node": "pre_filter"})
    data = state.get("input_data") or {}
    title = data.get("title", "")
    description = data.get("description", "")
    thread_id = state.get("thread_id")
    firestore_service.update_job_status(thread_id, "CHECKING_SAFETY")
    
    try:
        result = ai_service.analyze_listing_safety(title, description)
        
        if result.get("is_critical"):
            return {
                "early_blocked": True,
                "final_action": "Block",
                "risk_score": 1.0,
                "reasoning": f"Bloqueo automático: {result.get('reason', 'Contenido prohibido')}"
            }
    if not result.get("is_critical"):
        firestore_service.update_job_status(thread_id, "ANALYZING_IMAGE")
        
    return {"early_blocked": False}



# ================================================================
# Nodo 1: Feature Extractor (Multimodal LLM Evidence Generator)
# ================================================================
@measure_latency("feature_extractor")
def feature_extractor_node(state: AgentState):
    logger.info("node_started", extra={"node": "feature_extractor"})
    data = state["input_data"]
    gcs_uri = state.get("gcs_uri")
    audit_log = list(state.get("audit_log") or [])

    thread_id = state.get("thread_id")
    # Status updated at the end of previous node (pre_filter)

    if not gcs_uri:
        error_msg = "Missing GCS URI in state"
        logger.error(error_msg)
        audit_log.append({
            "node": "extractor", "status": "error",
            "summary": error_msg,
            "data": {"error": "missing_gcs_uri"},
            "evidence": {},
            "timestamp": _timestamp(),
        })
        return {
            "dissonance_detected": False,
            "features": {"error": "missing_gcs_uri"},
            "signals": {"image_not_found": True},
            "risk_score": 1.0,
            "audit_log": audit_log,
        }

    try:
        features = ai_service.extract_multimodal_features(gcs_uri, data)
        if "error" in features:
            raise Exception(features["error"])
            
        logger.debug("gemini_raw_features", extra={"node": "feature_extractor", "features": features})
        
        # Link state-level dissonance_detected to the new feature field
        visual_dissonance = features.get("visual_dissonance", False)
        contact_info = features.get("contact_info_detected", False)
        condition_issue = features.get("condition_issue_detected", False)
        
        dissonance = visual_dissonance or contact_info or condition_issue

        summary = (
            f"Evidence generated. Category: '{features.get('object_category')}'. "
            f"Sellable: {features.get('is_sellable')}. Dissonance: {visual_dissonance}. "
            f"Contact info: {contact_info}."
        )

        audit_log.append({
            "node": "extractor", "status": "completed", "summary": summary,
            "data": features,
            "evidence": {"image_analysis": features},
            "timestamp": _timestamp(),
        })

        firestore_service.update_job_status(thread_id, "APPLYING_POLICIES")

        return {
            "features": features, 
            "dissonance_detected": dissonance, 
            "signals": {},
            "risk_score": 0.0,
            "audit_log": audit_log
        }
    except Exception as e:
        error_msg = f"Gemini multimodal analysis failed: {e}"
        logger.error(error_msg)
        audit_log.append({
            "node": "extractor", "status": "error",
            "summary": error_msg,
            "data": {"error": "extraction_failed"}, "evidence": {},
            "timestamp": _timestamp(),
        })
        return {
            "features": {"error": "extraction_failed"}, 
            "dissonance_detected": False, 
            "signals": {},
            "risk_score": 1.0,
            "audit_log": audit_log
        }


# ================================================================
# Nodo 1.5: Policy Engine (Deterministic Rules)
# ================================================================
@measure_latency("policy_engine")
def policy_engine_node(state: AgentState):
    logger.info("node_started", extra={"node": "policy_engine"})
    # Status updated at the end of previous node (feature_extractor)
    features = state.get("features") or {}
    audit_log = list(state.get("audit_log") or [])
    
    primary_object = features.get("primary_object", "").lower()
    object_category = features.get("object_category", "").lower()
    product_condition = features.get("product_condition", "")
    image_quality = features.get("image_quality", "")
    image_type = features.get("image_type", "")
    contact_info_detected = features.get("contact_info_detected", False)
    is_sellable = features.get("is_sellable", True)
    
    policy_signals = {}
    
    # Rule 1 — banned object
    # HARD SAFETY RULE: Prevent illegal marketplace listings such as animals or humans.
    banned_keywords = [
        "dog","puppy","cat","kitten","animal",
        "person","human","baby","child",
        "blood","corpse","body"
    ]

    combined_text = f"{primary_object} {object_category}".lower()
    if any(keyword in combined_text for keyword in banned_keywords):
        policy_signals["banned_object"] = True
        
    # Rule 2 — unusable product
    if not is_sellable or product_condition in ["rotten", "damaged", "very_poor_quality"]:
        policy_signals["product_unusable"] = True
        
    # Rule 3 — low quality listing image
    if image_quality == "low":
        policy_signals["low_quality_image"] = True
        
    # Rule 4 — external contact info
    if contact_info_detected is True:
        policy_signals["external_contact"] = True

    # Rule 5 — Rule for suspicious image type (Extension)
    if image_type in ["screenshot", "stock_photo"]:
        # We can treat screenshots as low quality or a specific fraud signal in later stages
        if image_type == "screenshot":
            policy_signals["low_quality_image"] = True
        
    active_signals = [k for k, v in policy_signals.items() if v]
    summary = f"Active policy signals: {', '.join(active_signals)}" if active_signals else "No policy violations detected."
    
    audit_log.append({
        "node": "policy_engine",
        "status": "completed",
        "summary": summary,
        "data": policy_signals,
        "evidence": {"features_used": features, "is_sellable": is_sellable, "image_type": image_type},
        "timestamp": _timestamp(),
    })
    
    firestore_service.update_job_status(state.get("thread_id"), "SEARCHING_POLICIES")
    
    return {"policy_signals": policy_signals, "audit_log": audit_log}


# ================================================================
# Nodo 2: Vertex RAG (Policy Search)
# ================================================================
@measure_latency("rag_search")
def vertex_rag_node(state: AgentState):
    logger.info("node_started", extra={"node": "rag_search"})
    thread_id = state.get("thread_id")
    # Status updated at the end of previous node (policy_engine)
    
    features = state["features"]
    audit_log = list(state.get("audit_log") or [])
    
    # Use the new primary_object key
    obj_name = features.get('primary_object') or features.get('primary_object_in_image') or "unknown"
    query = f"Politicas e-commerce sobre {obj_name} y links de contacto o disonancia visual"

    client = discoveryengine.SearchServiceClient()
    serving_config = (
        f"projects/{PROJECT_ID}/locations/global/collections/default_collection"
        f"/engines/{DATA_STORE_ID}/servingConfigs/default_search"
    )

    rag_context = ""
    policy_citations = []

    try:
        request = discoveryengine.SearchRequest(
            serving_config=serving_config, query=query, page_size=3,
        )
        response = client.search(request)
        for idx, result in enumerate(response.results):
            derived_data = result.document.derived_struct_data
            doc_title = derived_data.get("title", "Untitled Policy") if derived_data else "Untitled Policy"
            if derived_data and "snippets" in derived_data:
                for snippet in derived_data["snippets"]:
                    snippet_text = snippet.get("snippet", "")
                    relevance = round(snippet.get("snippet_score", 0.0), 3)
                    rag_context += snippet_text + "\n"
                    policy_citations.append({
                        "policy_id": f"POL-{idx + 1}",
                        "policy_title": doc_title,
                        "snippet": snippet_text,
                        "reason": "",
                        "relevance_score": relevance,
                    })
    except Exception as e:
        print(f"Error en RAG Search: {e}")
        rag_context = "No se pudo recuperar contexto de politicas."

    policy_citations = sorted(policy_citations, key=lambda c: c["relevance_score"], reverse=True)[:3]

    audit_log.append({
        "node": "rag", "status": "completed",
        "summary": f"Retrieved {len(policy_citations)} policy citations.",
        "data": {"query": query, "policy_matches": policy_citations},
        "evidence": {"snippets": [c["snippet"] for c in policy_citations]},
        "timestamp": _timestamp(),
    })

    firestore_service.update_job_status(thread_id, "CALCULATING_RISK")

    return {"rag_context": rag_context, "policy_citations": policy_citations, "audit_log": audit_log}


# ================================================================
# Nodo 3: Signal Builder (DETERMINISTIC - no LLM)
# ================================================================
@measure_latency("signal_builder")
def signal_builder_node(state: AgentState):
    logger.info("node_started", extra={"node": "signal_builder"})
    features = state.get("features") or {}
    data = state["input_data"]
    policy_citations = state.get("policy_citations") or []
    policy_signals = dict(state.get("policy_signals") or {})
    audit_log = list(state.get("audit_log") or [])

    # Derive boolean signals from evidence
    visual_dissonance = bool(features.get("visual_dissonance", False))
    contact_info = bool(features.get("contact_info_detected", False))
    condition_issue = bool(features.get("condition_issue_detected", False))

    # Price anomaly heuristic
    price = float(data.get("price", 0))
    title_lower = data.get("title", "").lower()
    high_value_keywords = ["macbook", "iphone", "ipad", "samsung", "tv", "playstation", "xbox", "nvidia"]
    is_high_value = any(kw in title_lower for kw in high_value_keywords)
    price_anomaly = bool(is_high_value and 0 < price < 50)

    # Policy match: true if RAG returned relevant citations
    policy_match = len(policy_citations) > 0

    # Base signals
    signals = {
        "visual_dissonance": visual_dissonance,
        "contact_info_detected": contact_info,
        "price_anomaly": price_anomaly,
        "condition_issue": condition_issue,
        "policy_match": policy_match,
    }
    
    # Merge with policy_signals from deterministic node
    for k, v in policy_signals.items():
        signals[k] = bool(v)

    active = [k for k, v in signals.items() if v]
    summary = f"Signals active: {', '.join(active)}." if active else "No risk signals detected."

    audit_log.append({
        "node": "signal_builder", "status": "completed", "summary": summary,
        "data": signals, "evidence": {"features": features, "price": price, "policy_signals": policy_signals},
        "timestamp": _timestamp(),
    })

    logger.info("signals_generated", extra={
        "node": "signal_builder", 
        "features": features, 
        "policy_signals": policy_signals,
        "final_signals": signals
    })
    return {"signals": signals, "audit_log": audit_log}


# ================================================================
# Nodo 4: Risk Aggregator (DETERMINISTIC - no LLM)
# ================================================================
@measure_latency("risk_aggregation")
def risk_aggregator_node(state: AgentState):
    logger.info("node_started", extra={"node": "risk_aggregator"})
    # Status updated at the end of previous node (vertex_rag)
    signals = state.get("signals") or {}
    logger.info("risk_input_signals", extra={"node": "risk_aggregator", "signals": signals})
    audit_log = list(state.get("audit_log") or [])

    # HARD SAFETY RULE: Banned objects always produce maximum risk
    if signals.get("banned_object"):
        risk_score = 1.0
        summary = "CRITICAL: Hard safety rule triggered due to banned_object. Maximum risk score assigned."
        audit_log.append({
            "node": "risk_aggregator", "status": "completed", "summary": summary,
            "data": {"risk_score": 1.0, "reason": "banned_object_hard_block"},
            "evidence": {"signals": signals},
            "timestamp": _timestamp(),
        })
        return {
            "risk_score": 1.0, 
            "risk_breakdown": [{"factor": "banned_object", "weight": 1.0}], 
            "audit_log": audit_log
        }

    total_weight = 0.0
    risk_breakdown = []

    for signal_name, is_active in signals.items():
        if is_active and signal_name in RISK_WEIGHTS:
            weight = RISK_WEIGHTS[signal_name]
            total_weight += weight
            risk_breakdown.append({"factor": signal_name, "weight": weight})

    risk_score = min(total_weight, 1.0)

    summary = f"Risk score: {risk_score:.2f} (Total weight: {total_weight:.2f}). Signals: {', '.join(f'{b['factor']}({b['weight']})' for b in risk_breakdown)}"

    audit_log.append({
        "node": "risk_aggregator", "status": "completed", "summary": summary,
        "data": {
            "risk_score": risk_score, 
            "total_weight": total_weight,
            "risk_breakdown": risk_breakdown
        },
        "evidence": {"signals": signals, "weights": RISK_WEIGHTS},
        "timestamp": _timestamp(),
    })

    return {"risk_score": risk_score, "risk_breakdown": risk_breakdown, "audit_log": audit_log}


# ================================================================
# Nodo 5: LLM Explainer (LLM for explanation only, NOT scoring)
# ================================================================
@measure_latency("llm_explainer")
def llm_explainer_node(state: AgentState):
    logger.info("node_started", extra={"node": "llm_explainer"})
    signals = state.get("signals") or {}
    features = state.get("features") or {}
    rag_context = state.get("rag_context", "")
    risk_score = state.get("risk_score", 0.0)
    risk_breakdown = state.get("risk_breakdown") or []
    policy_citations = state.get("policy_citations") or []
    data = state["input_data"]
    audit_log = list(state.get("audit_log") or [])

    citations_text = ""
    for c in policy_citations:
        citations_text += f"  - [{c['policy_id']}] {c['policy_title']}: \"{c['snippet']}\"\n"

    breakdown_text = ", ".join(f"{b['factor']}({b['weight']})" for b in risk_breakdown)

    prompt = f"""
    A moderation system has analyzed the following product:
    Title: {data['title']}
    Price: ${data.get('price', 'N/A')}
    
    Detected signals: {json.dumps(signals)}
    Risk score (pre-computed): {risk_score:.2f}
    Risk breakdown: {breakdown_text}
    Extracted features: {json.dumps(features)}
    
    Policy citations:
{citations_text if citations_text else "    None retrieved."}

    Generate a concise explanation (2-3 sentences max) describing why the product was flagged or approved.
    Reference the detected signals and any relevant policies.
    Do NOT recompute or change the risk score.
    
    Return JSON:
    {{
        "reasoning": "concise explanation",
        "policy_violations": [
            {{
                "policy_id": "from citations above",
                "factor": "signal name",
                "explanation": "one sentence"
            }}
        ]
    }}
    """

    try:
        model = ai_service.get_gemini_model("gemini-1.5-flash")
        response = model.generate_content(prompt)
        result = ai_service._clean_and_parse_json(response.text)
        reasoning = result.get("reasoning", "No explanation generated.")
        policy_violations = result.get("policy_violations", [])
    except Exception as e:
        print(f"Error in LLM explainer: {e}")
        reasoning = f"Risk score {risk_score:.2f} computed from signals: {breakdown_text}."
        policy_violations = []

    # Enrich citations with reasons
    enriched_citations = list(policy_citations)
    for v in policy_violations:
        for c in enriched_citations:
            if c["policy_id"] == v.get("policy_id"):
                c["reason"] = v.get("explanation", "")

    audit_log.append({
        "node": "explainer", "status": "completed", "summary": reasoning[:120],
        "data": {"reasoning": reasoning, "policy_violations": policy_violations},
        "evidence": {"signals": signals, "risk_breakdown": risk_breakdown},
        "timestamp": _timestamp(),
    })

    return {
        "reasoning": reasoning,
        "policy_citations": enriched_citations,
        "policy_violations": policy_violations,
        "audit_log": audit_log,
    }


# ================================================================
# Nodo 6: Confidence Evaluation (DETERMINISTIC)
# ================================================================
@measure_latency("confidence_evaluation")
def confidence_evaluation_node(state: AgentState):
    logger.info("node_started", extra={"node": "confidence_evaluation"})
    features = state.get("features") or {}
    confidence = float(features.get("confidence", 1.0))
    uncertainty = 1.0 - confidence
    audit_log = list(state.get("audit_log") or [])

    summary = f"Confidence: {confidence:.2f}, Uncertainty: {uncertainty:.2f}"

    audit_log.append({
        "node": "confidence_eval", "status": "completed", "summary": summary,
        "data": {"confidence": confidence, "uncertainty": uncertainty},
        "evidence": {"features_confidence": confidence},
        "timestamp": _timestamp(),
    })

    return {"uncertainty": uncertainty, "audit_log": audit_log}


# ================================================================
# Nodo 7: Decision (DETERMINISTIC with Uncertainty Routing)
# ================================================================
@measure_latency("decision")
def decision_node(state: AgentState):
    logger.info("node_started", extra={"node": "decision"})
    score = state["risk_score"]
    uncertainty = state.get("uncertainty", 0.0)
    audit_log = list(state.get("audit_log") or [])
    policy_citations = state.get("policy_citations") or []
    policy_violations = state.get("policy_violations") or []

    # Thresholds
    # risk_score >= 0.7 → BLOCK
    # risk_score < 0.3 → APPROVE
    # 0.3 <= risk_score < 0.7 OR uncertainty > 0.4 → HUMAN_REVIEW
    
    requires_human_intervention = False

    if score >= 0.7:
        action = "Block"
        summary = f"Risk score {score:.2f} >= 0.7. Action: Block."
    elif score < 0.3:
        action = "Approve"
        summary = f"Risk score {score:.2f} < 0.3. Action: Approve."
    else:
        action = "Human Review"
        requires_human_intervention = True
        summary = f"Risk score {score:.2f} in [0.3, 0.7). Action: Human Review."

    if uncertainty > 0.4 and action != "Block":
        action = "Human Review"
        requires_human_intervention = True
        summary = f"Uncertainty {uncertainty:.2f} > 0.4. Action: Human Review."

    if policy_violations:
        violated_ids = ", ".join(v.get("policy_id", "?") for v in policy_violations)
        summary += f" Policies violated: {violated_ids}."

    audit_log.append({
        "node": "decision", "status": "completed", "summary": summary,
        "data": {
            "risk_score": score,
            "uncertainty": uncertainty,
            "final_action": action,
            "requires_human_intervention": requires_human_intervention,
            "policy_violations": policy_violations
        },
        "evidence": {"policy_citations": policy_citations},
        "timestamp": _timestamp(),
    })

    # Update Firestore with final result
    status_map = {
        "Approve": "APPROVED",
        "Block": "REJECTED",
        "Human Review": "MANUAL_REVIEW"
    }
    final_status = status_map.get(action, "UNKNOWN")
    thread_id = state.get("thread_id")
    firestore_service.update_job_status(
        thread_id, 
        final_status, 
        metadata={"risk_score": score, "final_action": action}
    )

    return {
        "final_action": action,
        "requires_human_intervention": requires_human_intervention,
        "policy_citations": policy_citations,
        "policy_violations": policy_violations,
        "audit_log": audit_log,
    }


# ================================================================
# Nodo 8: Data Flywheel (BigQuery Audit Sink)
# ================================================================
@measure_latency("data_flywheel")
def data_flywheel_node(state: AgentState):
    logger.info("node_started", extra={"node": "data_flywheel"})
    
    try:
        bq_client = bigquery.Client()
        # Inserción en la tabla especificada por el usuario
        table_id = f"{PROJECT_ID}.moderation_dataset.evaluations"
        
        # Preparación del diccionario con los campos exactos solicitados
        row = {
            "thread_id": state.get("thread_id"),
            "risk_score": float(state.get("risk_score", 0.0)),
            "final_action": state.get("final_action"),
            "reasoning": state.get("reasoning"),
            "is_early_blocked": bool(state.get("early_blocked", False)),
            "timestamp": _timestamp(),
        }
        
        # Inserción en BigQuery usando insert_rows_json
        errors = bq_client.insert_rows_json(table_id, [row])
        
        if errors:
            # Logueo del error pero sin romper el flujo (graceful failure)
            logger.error(f"BigQuery insertion errors: {errors}")
            
    except Exception as e:
        # Fallo suave ante cualquier excepción para asegurar que el grafo se cierre correctamente
        logger.error(f"Graceful failure in data_flywheel_node BigQuery sink: {e}")
        
    # Devuelve un diccionario vacío para seguir mejores prácticas de LangGraph (sink node)
    return {}
