import os
import json
import re
import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.cloud import bigquery
from langgraph.types import interrupt
from langchain_core.runnables import RunnableConfig
from .state import AgentState
from .utils.prompt_loader import load_prompt
from .services.ai_service import get_gemini_model
from .schemas import ExplanationResponse
from .services import ai_service, firestore_service, rag_service
from .constants import RISK_WEIGHTS

background_tasks = set()

async def run_background(coro):
    """Safely dispatches background tasks, executing them synchronously in tests to avoid hangs."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        await coro
    else:
        task = asyncio.create_task(coro)
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)


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



def measure_latency(span_name: Optional[str] = None):
    """Decorator to measure and log node execution time and trace spans (Sync/Async)."""
    def decorator(func):
        # pyrefly: ignore [deprecated]
        if asyncio.iscoroutinefunction(func):
            async def wrapper(state: AgentState, config: RunnableConfig, *args, **kwargs):
                nonlocal span_name
                actual_span_name = span_name or func.__name__.replace("_node", "")
                with tracer.start_as_current_span(actual_span_name):
                    start_time = time.time()
                    result = await func(state, config, *args, **kwargs)
                    latency_ms = (time.time() - start_time) * 1000
                    pipeline_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id", "unknown")
                    logger.info("node_latency", extra={"node": actual_span_name, "latency_ms": latency_ms, "pipeline_id": pipeline_id})
                    
                    if isinstance(result, dict):
                        metrics = result.setdefault("execution_metrics", {})
                        nodes = metrics.setdefault("nodes", {})
                        node_metrics = nodes.setdefault(actual_span_name, {})
                        node_metrics["latency_ms"] = latency_ms
                        
                    return result
            return wrapper
        else:
            def wrapper(state: AgentState, config: RunnableConfig, *args, **kwargs):
                nonlocal span_name
                actual_span_name = span_name or func.__name__.replace("_node", "")
                with tracer.start_as_current_span(actual_span_name):
                    start_time = time.time()
                    result = func(state, config, *args, **kwargs)
                    latency_ms = (time.time() - start_time) * 1000
                    pipeline_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id", "unknown")
                    logger.info("node_latency", extra={"node": actual_span_name, "latency_ms": latency_ms, "pipeline_id": pipeline_id})
                    
                    if isinstance(result, dict):
                        metrics = result.setdefault("execution_metrics", {})
                        nodes = metrics.setdefault("nodes", {})
                        node_metrics = nodes.setdefault(actual_span_name, {})
                        node_metrics["latency_ms"] = latency_ms
                        
                    return result
            return wrapper
    return decorator



# Constants with fallback for remote environment
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
DATA_STORE_ID = os.getenv("DATA_STORE_ID")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_json_string(raw_text: str) -> str:
    """Elimina bloques de Markdown y caracteres de control ASCII que rompen json.loads."""
    if not raw_text:
        return "{}"
    # Quita los tags de bloque de código markdown si existen
    clean = re.sub(r"```json|```", "", raw_text).strip()
    # Elimina caracteres de control (0-31) y otros no imprimibles que causan el error
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", clean)
    return clean


# ================================================================
# Nodo 0: Pre-Filter (Critical Violation Check)
# ================================================================  
@measure_latency("pre_filter")
async def pre_filter_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "pre_filter"})
    data = state.get("input_data") or {}
    title = data.get("title", "")
    description = data.get("description", "")
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    # Ejecución en segundo plano (Fire-and-Forget) con manejo interno de errores.
    # El agente continúa inmediatamente con la llamada al LLM sin esperar a Firestore.
    async def safe_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "CHECKING_SAFETY")
        except Exception as e:
            logger.error(f"Non-blocking background error updating Firestore status: {e}", exc_info=True)

    asyncio.create_task(safe_status_update())
    
    try:
        service_result = await ai_service.analyze_safety(title, description)
        data = service_result.get("data", {})
        usage = service_result.get("usage", {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"})
        
        if data.get("is_critical"):
            return {
                "early_blocked": True,
                "routing_reason": "early_block",
                "violation_category": "Critical",
                "final_action": "Block",
                "risk_score": 1.0,
                "reasoning": f"Bloqueo automático: {data.get('reason', 'Contenido prohibido')}",
                "execution_metrics": {"nodes": {"pre_filter": usage}}
            }
 
        return {"early_blocked": False, "routing_reason": None, "execution_metrics": {"nodes": {"pre_filter": usage}}}
    except Exception as e:
        logger.error(f"Error in pre_filter safety check: {e}")
        usage = {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "error"}

        
    return {"early_blocked": False, "routing_reason": None, "execution_metrics": {"nodes": {"pre_filter": usage}}}


# ================================================================
# Nodo 1: Feature Extractor (Multimodal LLM Evidence Generator)
# ================================================================
@measure_latency("extractor")
async def feature_extractor_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "extractor"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    async def safe_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "ANALYZING_IMAGE")
        except Exception as e:
            logger.error(f"Non-blocking background error updating Firestore status: {e}", exc_info=True)

    asyncio.create_task(safe_status_update())

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
            "audit_log": [{
                "node": "extractor", "status": "error",
                "summary": error_msg,
                "data": {"error": "missing_gcs_uri"},
                "evidence": {},
                "timestamp": _timestamp(),
            }],
            "execution_metrics": {"nodes": {"extractor": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}}}
        }

    try:
        service_result = await ai_service.extract_multimodal_features(gcs_uri, data)
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
                # CAMBIO 2: era risk_score: 0.8 (zona de Block) → 0.5 (zona gris) + señal explícita
                "risk_score": 0.5,
                "extraction_failed": True,
                "min_market_price": 0.0,
                "max_market_price": float('inf'),
                "audit_log": [{
                    "node": "extractor", "status": "error",
                    "summary": error_msg,
                    "data": features, "evidence": {},
                    "timestamp": _timestamp(),
                }],
                "execution_metrics": {"nodes": {"extractor": usage}}
            }

        visual_dissonance = features.get("visual_dissonance", False)
        contact_info = features.get("contact_info_detected", False)
        condition_issue = features.get("condition_issue_detected", False)

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
            "min_market_price": min_market_price,
            "max_market_price": max_market_price,
            "signals": {"visual_dissonance": visual_dissonance},
            "image_quality_score": features.get("image_quality_score", 0.0),
            "routing_reason": routing_reason,
            "risk_score": 0.0,
            "audit_log": [{
                "node": "extractor", "status": "completed", "summary": summary,
                "data": features,
                "evidence": {"image_analysis": features},
                "timestamp": _timestamp(),
            }],
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
            "audit_log": [{
                "node": "extractor", "status": "error",
                "summary": error_msg,
                "data": {"error": "extraction_failed"}, "evidence": {},
                "timestamp": _timestamp(),
            }],
            "execution_metrics": {"nodes": {"extractor": usage}}
        }

# ================================================================
# Nodo 2: Vertex RAG (Policy Search)
# ================================================================
@measure_latency("rag")
async def rag_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "rag"})
    
    features = state.get("features") or {}
    data = state.get("input_data") or {}
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    # 1. Registro de estado en segundo plano (Fire-and-Forget) para mantener la fluidez en tiempo real
    async def safe_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "SEARCHING_POLICIES")
        except Exception as e:
            logger.error(f"Non-blocking background error updating Firestore status: {e}", exc_info=True)

    asyncio.create_task(safe_status_update())

    # ===== PHASE 1: Policy Search =====
    obj_name = features.get('primary_object') or features.get('primary_object_in_image') or "unknown"
    query = f"Politicas e-commerce sobre {obj_name} y links de contacto o disonancia visual"

    try:
        # Recuperamos estrictamente las 2 variables de políticas
        rag_context, policy_citations = await rag_service.search_policies(query)
    except Exception as e:
        logger.error(f"RAG service failed: {e}", exc_info=True)
        rag_context = "No se pudo recuperar contexto de políticas. Error técnico."
        policy_citations = []

    usage = {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}
    # Phase 2 (Reason Generation) eliminada por duplicación de llamadas, relegada al nodo decision.

    # ===== PHASE 3: Return Updated State =====
    # Eliminamos toda referencia a min_market_price y max_market_price.
    # Al no incluirlos en el return, LangGraph preserva los valores exactos que dejó el Nodo 1.
    return {
        "rag_context": rag_context,
        "policy_citations": policy_citations,
        "audit_log": [{
            "node": "rag", 
            "status": "completed",
            "summary": f"Retrieved {len(policy_citations)} policy citations for object '{obj_name}'.",
            "data": {
                "query": query, 
                "policy_matches": policy_citations
            },
            "evidence": {"snippets": [c.get("snippet", "") for c in policy_citations if isinstance(c, dict)]},
            "timestamp": _timestamp(),
        }],
        "execution_metrics": {"nodes": {"rag": usage}}
    }

# ================================================================
# Nodo 3: Risk Evaluator 
# ================================================================
@measure_latency("risk_evaluator")
async def risk_evaluator_node(state: AgentState, config: RunnableConfig): 
    logger.info("node_started", extra={"node": "risk_evaluator"})
    
    # PHASE 1: Logic Processing (Deterministic Rules & Signals)
    features = state.get("features") or {}
    data = state.get("input_data") or {}
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    async def safe_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "EVALUATING_RISK")
        except Exception as e:
            logger.error(f"Non-blocking background error updating Firestore status: {e}", exc_info=True)

    asyncio.create_task(safe_status_update())
    
    # 1. Reglas de Policy Engine
    primary_object = features.get("primary_object", "").lower()
    object_category = features.get("object_category", "").lower()
    product_condition = features.get("product_condition", "")
    image_quality = features.get("image_quality", "")
    image_type = features.get("image_type", "")
    contact_info_detected = features.get("contact_info_detected", False)
    is_sellable = features.get("is_sellable", True)
    
    signals = {}

    # Keywords siempre prohibidos independientemente del contexto visual
    banned_product_keywords = [
        "person", "human", "baby", "child",
        "blood", "corpse", "body"
    ]

    # FIX MASCOTAS: animales separados — solo se bloquean si el animal ES el producto,
    # no si aparece como contexto visual de un accesorio
    animal_keywords = ["dog", "puppy", "cat", "kitten", "animal", "bird", "fish", "reptile"]

    combined_text = f"{primary_object} {object_category}".lower()
    title_lower = data.get("title", "").lower()
    description_lower = data.get("description", "").lower()
    listing_text = f"{title_lower} {description_lower}"

    # Objetos siempre prohibidos
    if any(keyword in combined_text for keyword in banned_product_keywords):
        signals["banned_object"] = True

    # Animales: solo bloqueamos si el animal parece ser el producto en venta
    elif any(keyword in combined_text for keyword in animal_keywords):
        animal_as_product_indicators = [
            "vendo", "venta", "cachorro", "cría", "camada",
            "mascota en venta", "adopción", "permuto"
        ]
        accessory_indicators = [
            "para perro", "para gato", "para mascota", "accesorio",
            "ropa para", "cama para", "colchón para", "piloto para",
            "juguete para", "collar", "correa", "bowl", "comedero"
        ]

        is_accessory = any(ind in listing_text for ind in accessory_indicators)
        is_animal_product = any(ind in listing_text for ind in animal_as_product_indicators)

        if is_animal_product and not is_accessory:
            signals["banned_object"] = True
        elif not is_accessory:
            signals["animal_in_image_ambiguous"] = True

    # Unusable product
    if not is_sellable or product_condition in ["rotten", "damaged", "very_poor_quality"]:
        signals["product_unusable"] = True
        
    # FIX IMAGEN NO VERIFICABLE: separado de low_quality_image genérico.
    # Una imagen que no permite verificación visual no puede aprobarse automáticamente
    # independientemente de lo que diga el texto — siempre debe ir a HITL.
    if image_quality == "low":
        signals["low_quality_image"] = True
        signals["unverifiable_image"] = True

    # Imagen sospechosa por tipo (screenshot, stock) pero no necesariamente no verificable
    if image_type in ["screenshot", "stock_photo"]:
        signals["low_quality_image"] = True
        
    # External contact info
    if contact_info_detected:
        signals["external_contact"] = True
        signals["contact_info_detected"] = True

    # 2. Lógica de Signal Builder
    signals["visual_dissonance"] = bool(features.get("visual_dissonance", False))
    signals["condition_issue"] = bool(features.get("condition_issue_detected", False))

    # ================================================================
    # Price anomaly validation (Dynamic Firestore Thresholds)
    # ================================================================
    price = float(data.get("price", 0))
    min_market_price = float(state.get("min_market_price", 0.0))
    max_market_price = float(state.get("max_market_price", float('inf')))
    
    if min_market_price > 0.0 or max_market_price < float('inf'):
        signals["price_anomaly"] = bool(price < min_market_price or price > max_market_price)
    else:
        high_value_keywords = ["macbook", "iphone", "ipad", "samsung", "tv", "playstation", "xbox", "nvidia"]
        is_high_value = any(kw in title_lower for kw in high_value_keywords)
        signals["price_anomaly"] = bool(is_high_value and 0 < price < 50)
    
    active_signals = [k for k, v in signals.items() if v]
    logic_summary = f"Logic signals: {', '.join(active_signals)}" if active_signals else "No logic violations detected."
    
    # PHASE 2: Risk Aggregation (Weighted Scoring)
    total_weight = 0.0
    risk_breakdown = []

    global_weights = globals().get("RISK_WEIGHTS", {})
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
            "audit_log": [{
                "node": "risk_evaluator", "status": "completed", "summary": summary,
                "data": {"risk_score": 1.0, "reason": "banned_object_hard_block", "signals": signals},
                "evidence": {"signals": signals, "features_used": features, "price": price},
                "timestamp": _timestamp(),
            }],
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
        "audit_log": [{
            "node": "risk_evaluator", "status": "completed", "summary": summary,
            "data": {
                "signals": signals,
                "risk_score": risk_score, 
                "total_weight": total_weight,
                "risk_breakdown": risk_breakdown
            },
            "evidence": {"signals": signals, "weights": global_weights, "features_used": features, "price": price},
            "timestamp": _timestamp(),
        }],
        "execution_metrics": {"nodes": {"risk_evaluator": {"prompt_tokens": 0, "candidates_tokens": 0, "model_name": "none"}}}
    }

    
# ================================================================
# Nodo 4: LLM Reasoning (LLM for explanation only, NOT scoring)
# ================================================================
@measure_latency("reasoning")
async def llm_reasoning_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "reasoning"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    # 1. Registro de estado inicial no bloqueante (Fire-and-Forget) para el frontend
    async def safe_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "GENERATING_REASONING")
        except Exception as e:
            logger.error(f"Non-blocking background error updating Firestore status: {e}", exc_info=True)

    asyncio.create_task(safe_status_update())
    
    # CORRECCIÓN DE SEGURIDAD: Uso seguro de .get() para evitar KeyError si input_data no existe
    data = state.get("input_data") or {}
    
    # CORRECCIÓN DE SEGURIDAD: Uso defensivo de .get() dentro de list comprehensions para evitar caídas del grafo
    citations_list = state.get("policy_citations") or []
    citations_text = "\n".join([
        f" - [{c.get('policy_id', 'N/A')}] {c.get('policy_title', 'Sin Título')}: \"{c.get('snippet', '')}\"" 
        for c in citations_list if isinstance(c, dict)
    ])
    
    breakdown_list = state.get("risk_breakdown") or []
    breakdown_text = ", ".join(
        f"{b.get('factor', 'unknown')}({b.get('weight', 0.0)})" 
        for b in breakdown_list if isinstance(b, dict)
    )

    # Extract price thresholds from state
    min_market_price = state.get("min_market_price", 0.0)
    max_market_price = state.get("max_market_price", float('inf'))
    
    # Format price bounds for prompt
    if min_market_price == 0.0 and max_market_price == float('inf'):
        price_bounds_text = "Rango de mercado: No disponible para esta categoría"
    else:
        price_bounds_text = f"Rango de mercado esperado: ${min_market_price:,.0f} - ${max_market_price:,.0f} ARS"

    # 2. Cargar y formatear prompt (Uso seguro de .get)
    raw_prompt = load_prompt("llm_explainer_prompt")
    prompt = raw_prompt.format(
        title=data.get('title', 'N/A'),
        price=data.get('price', 'N/A'),
        price_bounds=price_bounds_text,
        signals=json.dumps(state.get("signals", {})),
        risk_score=f"{state.get('risk_score', 0.0):.2f}",
        breakdown_text=breakdown_text,
        features=json.dumps(state.get("features", {})),
        citations_text=citations_text if citations_text else "None retrieved."
    )

    # 3. Llamada al servicio IA
    model = get_gemini_model("gemini-3.1-flash-lite-preview")
    
    # Valores por defecto para el error
    reasoning = f"Risk score {state.get('risk_score', 0.0):.2f} computed."
    policy_violations = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model_name": "error"}

    try:
        response = await model.generate_async(contents=prompt, response_schema=ExplanationResponse)
        
        # Extraer metadata de tokens de manera defensiva por cambios de API
        metadata = getattr(response, "usage_metadata", None)
        if metadata:
            usage = {
                "prompt_tokens": getattr(metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(metadata, "candidates_token_count", 0),
                "total_tokens": getattr(metadata, "total_token_count", 0),
                "model_name": "gemini-3.1-flash-lite-preview"
            }
        
        # Validar respuesta usando Pydantic
        result = ExplanationResponse.model_validate_json(response.text)
        reasoning = result.reasoning
        policy_violations = [v.model_dump() for v in result.policy_violations]
        
    except Exception as e:
        logger.error(f"Error in LLM explainer: {e}", exc_info=True)

    # 4. Enriquecer (Copia profunda/limpia para evitar mutaciones directas sobre el estado original)
    enriched_citations = [dict(c) for c in citations_list if isinstance(c, dict)]
    for v in policy_violations:
        if isinstance(v, dict):
            violation_id = v.get("policy_id")
            for c in enriched_citations:
                if c.get("policy_id") == violation_id: # CORRECCIÓN: .get() seguro en lugar de acceso directo por índice
                    c["reason"] = v.get("explanation", "")

    return {
        "reasoning": reasoning,
        "policy_citations": enriched_citations,
        "policy_violations": policy_violations,
        "usage_stats": usage,
        "execution_metrics": {"nodes": {"reasoning": {
            "prompt_tokens": usage["prompt_tokens"],
            "candidates_tokens": usage["completion_tokens"],
            "model_name": usage["model_name"]
        }}},
        "audit_log": [{
            "node": "reasoning",
            "status": "completed",
            "summary": f"Generated reasoning. Violations found: {len(policy_violations)}.",
            "data": {"policy_violations": policy_violations},
            "evidence": {"reasoning": reasoning},
            "timestamp": _timestamp(),
        }]
    }


# ================================================================
# Nodo 5: Decision (DETERMINISTIC with Uncertainty Routing)
# ================================================================
@measure_latency("decision")
async def decision_node(state: AgentState, config: RunnableConfig): 
    logger.info("node_started", extra={"node": "decision"})
    
    features = state.get("features") or {}
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    # CORRECCIÓN DE SEGURIDAD: Try-except preventivo por si el valor de confianza no es parseable
    try:
        confidence = float(features.get("confidence", 1.0))
    except (ValueError, TypeError):
        confidence = 1.0
        
    uncertainty = 1.0 - confidence
    
    # CORRECCIÓN DE SEGURIDAD: Evitamos KeyError usando .get() y aseguramos casteo a float
    score = float(state.get("risk_score", 0.0))
    
    policy_citations = state.get("policy_citations") or []
    policy_violations = state.get("policy_violations") or []

    # FIX 1B: Guard clause — si la extracción falló, derivar siempre a HITL
    # independientemente del score o la incertidumbre calculada.
    # Se ejecuta antes de cualquier lógica de scoring para que no pueda ser
    # sobreescrito por policy_match_weight ni por ninguna otra rama.
    if state.get("extraction_failed"):
        summary = "Feature extraction failed. Routing to human review."
        try:
            await firestore_service.update_job_status(
                thread_id,
                "MANUAL_REVIEW",
                metadata={"risk_score": score, "final_action": "Human Review"}
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
            "audit_log": [{
                "node": "decision",
                "status": "completed",
                "summary": summary,
                "data": {
                    "risk_score": score,
                    "final_action": "Human Review",
                    "requires_human_intervention": True,
                    "policy_violations": policy_violations,
                    "reason": "extraction_failed"
                },
                "evidence": {"policy_citations": policy_citations},
                "timestamp": _timestamp(),
            }],
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

    # Ajustar risk_score si hay policy_citations usando acceso defensivo al diccionario de pesos
    if policy_citations:
        global_weights = globals().get("RISK_WEIGHTS", {})
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

    # Incertidumbre alta (Fuerza Human Review a menos que ya sea un Block duro)
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
        # SEGURIDAD: Validación de tipo (isinstance) antes de llamar a .get()
        violated_ids = ", ".join(
            str(v.get("policy_id") or "?")
            for v in policy_violations if isinstance(v, dict)
        )
        summary += f" Policies violated: {violated_ids}."

    # Registro del veredicto final (Sincrónico y Crítico)
    # Bloqueante: Si falla, aborta el nodo para que el orquestador lo detecte.
    try:
        await firestore_service.update_job_status(
            thread_id,
            final_status,
            metadata={
                "risk_score": score,
                "final_action": action
            }
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
        "audit_log": [{
            "node": "decision",
            "status": "completed",
            "summary": summary,
            "data": {
                "risk_score": score,
                "final_action": action,
                "requires_human_intervention": requires_human_intervention,
                "policy_violations": policy_violations
            },
            "evidence": {"policy_citations": policy_citations},
            "timestamp": _timestamp(),
        }],
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

# ================================================================
# Nodo 6: Human Review (Manual Intervention)
# ================================================================
@measure_latency("human_in_the_loop")
async def human_review(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "human_in_the_loop"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")

    # 1. CORRECCIÓN CRÍTICA DE UX: Actualización de estado ANTES de la interrupción
    # Si no notificamos a Firestore AQUÍ, la base de datos se quedará con el estado del nodo anterior 
    # mientras el grafo esté pausado indefinidamente esperando al humano.
    async def safe_pending_status_update():
        try:
            await firestore_service.update_job_status(thread_id, "PENDING_HUMAN_REVIEW")
        except Exception as e:
            logger.error(f"Non-blocking background error setting PENDING_HUMAN_REVIEW: {e}", exc_info=True)

    await run_background(safe_pending_status_update())

    # Pausa de ejecución hasta recibir feedback (Mecanismo nativo de LangGraph)
    decision = interrupt({
        "mensaje": "Revisión requerida",
        "datos": state.get("reasoning", "No reasoning summary provided.")
    })

    feedback = decision if isinstance(decision, dict) else {}
    human_decision = feedback.get("decision")

    if human_decision == "Approve":
        final_action = "Approve"
        status = "APPROVE"
    elif human_decision == "Block":
        final_action = "Block"
        status = "BLOCK"
    else:
        # CORRECCIÓN DE ESQUEMA: Si se fuerza la reanudación del grafo sin datos válidos, 
        # devolvemos la estructura limpia del estado para no romper los reducers de LangGraph.
        return {
            "requires_human_intervention": True,
            "audit_log": [{
                "node": "human_in_the_loop",
                "status": "pending",
                "summary": "Graph was resumed but no valid human decision was matched.",
                "timestamp": _timestamp(),
            }],
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

    # 2. Registro del veredicto final en segundo plano (Fire-and-Forget)
    # Al igual que en los nodos deterministas previos, desacoplamos la persistencia de la salida del grafo.
    async def safe_final_status_update():
        try:
            await firestore_service.update_job_status(
                thread_id,
                status,
                metadata={
                    "human_reviewed": True,
                    "final_decision": human_decision
                }
            )
        except Exception as e:
            logger.error(f"Non-blocking background error saving human decision to Firestore: {e}", exc_info=True)

    await run_background(safe_final_status_update())

    return {
        "final_action": final_action,
        "human_feedback": feedback,
        "requires_human_intervention": False,
        "audit_log": [{
            "node": "human_in_the_loop",
            "status": "completed",
            "summary": f"Human review completed: {human_decision}.",
            "data": {"decision": human_decision},
            "timestamp": _timestamp(),
        }],
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



# ================================================================
# Nodo 7: Nodo de flywheel  
# ================================================================
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
        project_id = globals().get("PROJECT_ID", "unknown-project")
        table_id = f"{project_id}.moderation_dataset.evaluations"
        
        input_data = state.get("input_data") or {}
        features = state.get("features") or {}
        execution_metrics = state.get("execution_metrics") or {}
        
        row = {
            # --- Trazabilidad Base ---
            "thread_id": config.get("configurable", {}).get("thread_id") or state.get("thread_id"),
            "product_title": input_data.get("title"),
            "product_description": input_data.get("description"),
            "image_url": state.get("gcs_uri"),
            "risk_score": _safe_float(state.get("risk_score"), default=0.0),
            "final_action": current_action,
            "reasoning": state.get("reasoning"),
            "is_early_blocked": bool(state.get("early_blocked", False)),
            "timestamp": _timestamp(),
            "execution_metrics": json.dumps(execution_metrics),
            
            # --- Enriquecimiento para Data Flywheel ---
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
                logger.error(f"Background BigQuery insertion failed: {e}", exc_info=True)
                
        # Fire-and-forget
        await run_background(_safe_execute_insert())
            
    except Exception as e:
        logger.error(f"Graceful failure in data_flywheel_node BigQuery sink setup: {e}", exc_info=True)
        
    return {
        "audit_log": [{
            "node": "fly_wheel",
            "status": "completed",
            "summary": f"Data persisted for thread {state.get('thread_id')}",
            "timestamp": _timestamp()
        }],
        "final_action": current_action
    }