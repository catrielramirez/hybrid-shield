from typing import TypedDict, Optional

class AgentState(TypedDict):
    input_data: dict            # {"title": str, "description": str, "price": float}
    thread_id: str              # Unique session identifier
    gcs_uri: str                # Google Cloud Storage URI for the product image
    requires_human_intervention: bool    # Flag for LangGraph breakpoint
    human_feedback: Optional[dict]       # Manual decision from moderator
    early_blocked: bool                  # Flag for pre-filter rejection
    features: dict
    rag_context: str
    risk_score: float
    reasoning: str
    final_action: str           # "Approve", "Human Review", "Block"
    dissonance_detected: bool
    audit_log: list[dict]       # Structured audit trail
    policy_citations: list[dict]
    policy_violations: list[dict]
    signals: dict               # Deterministic boolean signals
    risk_breakdown: list[dict]  # Weighted factor breakdown
    uncertainty: float          # 1 - confidence
    policy_signals: dict        # Deterministic policy engine outputs

