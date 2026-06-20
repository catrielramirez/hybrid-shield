import json
import logging
import asyncio
from langchain_core.runnables import RunnableConfig
from ..state import AgentState
from ..schemas import ExplanationResponse
from ..services.ai_service import get_gemini_model
from ..utils.prompt_loader import load_prompt
from ..shared.observability import measure_latency
from ..shared.status_updates import emit_status
from ..shared.audit import make_audit_entry

logger = logging.getLogger("moderation_pipeline")


@measure_latency("reasoning")
async def llm_reasoning_node(state: AgentState, config: RunnableConfig):
    logger.info("node_started", extra={"node": "reasoning"})
    thread_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id")
    
    # 1. Simple status update (Pattern A)
    try:
        await emit_status(
            thread_id,
            "reasoning",
            "GENERATING_REASONING",
            "generating_reasoning",
            "Generando explicación detallada..."
        )
    except Exception as e:
        logger.error(f"Error updating Firestore status: {e}", exc_info=True)
    
    data = state.get("input_data") or {}
    
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

    # 2. Load and format prompt
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

    # 3. Setup function for LLM call
    async def generate_reasoning():
        model = get_gemini_model("gemini-2.5-flash")
        return await model.generate_async(contents=prompt, response_schema=ExplanationResponse)
    
    # Default values for error
    reasoning = f"Risk score {state.get('risk_score', 0.0):.2f} computed."
    policy_violations = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model_name": "error"}

    try:
        # Concurrent execution: UI status update + LLM reasoning generation
        _, response = await asyncio.gather(
            emit_status(
                thread_id,
                "reasoning",
                "GENERATING_REASONING",
                "generating_reasoning",
                "Generando explicación detallada..."
            ),
            generate_reasoning(),
            return_exceptions=False
        )
        
        # Extract token metadata defensively due to API changes
        metadata = getattr(response, "usage_metadata", None)
        if metadata:
            usage = {
                "prompt_tokens": getattr(metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(metadata, "candidates_token_count", 0),
                "total_tokens": getattr(metadata, "total_token_count", 0),
                "model_name": "gemini-2.5-flash"
            }
        
        # Validate response using Pydantic
        result = ExplanationResponse.model_validate_json(response.text)
        reasoning = result.reasoning
        policy_violations = [v.model_dump() for v in result.policy_violations]
        
    except Exception as e:
        logger.error(f"Error in LLM explainer: {e}", exc_info=True)

    # 4. Enrich citations (deep/clean copy to avoid mutating original state)
    enriched_citations = [dict(c) for c in citations_list if isinstance(c, dict)]
    for v in policy_violations:
        if isinstance(v, dict):
            violation_id = v.get("policy_id")
            for c in enriched_citations:
                if c.get("policy_id") == violation_id:
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
        "audit_log": [make_audit_entry(
            node="reasoning",
            status="completed",
            summary=f"Generated reasoning. Violations found: {len(policy_violations)}.",
            data={"policy_violations": policy_violations},
            evidence={"reasoning": reasoning}
        )]
    }
