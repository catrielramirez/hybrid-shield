from typing import TypedDict, Optional, Annotated
import operator
from .schemas import ViolationCategory


def merge_metrics(left: dict, right: dict) -> dict:
    if not left:
        left = {"totals": {"prompt_tokens": 0, "candidates_tokens": 0}, "nodes": {}}
    if not right:
        return left

    merged_totals = dict(left.get("totals", {"prompt_tokens": 0, "candidates_tokens": 0}))
    
    for node_name, usage in right.get("nodes", {}).items():
        merged_totals["prompt_tokens"] += usage.get("prompt_tokens", 0)
        merged_totals["candidates_tokens"] += usage.get("candidates_tokens", 0)

    merged_nodes = dict(left.get("nodes", {}))
    merged_nodes.update(right.get("nodes", {}))
    
    return {"totals": merged_totals, "nodes": merged_nodes}

class AgentState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    input_data: dict          # {"title": str, "description": str, "price": float}
    thread_id: str
    gcs_uri: str

    # ── Control flow ───────────────────────────────────────
    requires_human_intervention: bool
    human_feedback: Optional[dict]
    early_blocked: bool
    extraction_failed: bool       # fallo técnico del extractor → HITL
    unverifiable_image: bool      # imagen no verificable visualmente → HITL
    routing_reason: Optional[str] # "early_block" | "low_confidence" | "extraction_failed"
                                  # | "unverifiable_image" | "high_risk" | "approved" | "human_review"

    # ── Extractor output ───────────────────────────────────
    features: dict
    image_quality_score: float    # 0.0–1.0 del pre-check determinístico (brillo/varianza)

    # ── RAG ────────────────────────────────────────────────
    rag_context: str
    policy_citations: list[dict]  # [{policy_id, policy_title, snippet, reason, relevance_score}]
                                  # reason es obligatorio: explica por qué la política aplica al caso

    # ── Risk ───────────────────────────────────────────────
    signals: dict                 # fuente de verdad única para todos los flags booleanos de riesgo
                                  # keys: visual_dissonance, condition_issue, price_anomaly, ...
    risk_score: float
    risk_breakdown: list[dict]    # [{factor, weight, triggered, contribution}]
    uncertainty: float            # 1 - confidence, seteado por el nodo decision

    # ── Decision ───────────────────────────────────────────
    reasoning: str
    final_action: str             # "Approve" | "Human Review" | "Block"
    violation_category: Optional[ViolationCategory]
    policy_violations: list[dict]

    # ── Pricing ────────────────────────────────────────────
    min_market_price: float
    max_market_price: float

    # ── Observability ──────────────────────────────────────
    audit_log: Annotated[list[dict], operator.add]
    execution_metrics: Annotated[dict, merge_metrics]