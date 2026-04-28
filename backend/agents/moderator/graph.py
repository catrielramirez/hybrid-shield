from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AgentState
from .nodes import (
    pre_filter_node,
    feature_extractor_node,
    policy_engine_node,
    vertex_rag_node,
    signal_builder_node,
    risk_aggregator_node,
    llm_explainer_node,
    confidence_evaluation_node,
    decision_node,
    data_flywheel_node,
)


def create_moderator_graph():
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("pre_filter", pre_filter_node)
    workflow.add_node("extractor", feature_extractor_node)
    workflow.add_node("policy_engine", policy_engine_node)
    workflow.add_node("rag", vertex_rag_node)
    workflow.add_node("signal_builder", signal_builder_node)
    workflow.add_node("risk_aggregator", risk_aggregator_node)
    workflow.add_node("llm_explainer", llm_explainer_node)
    workflow.add_node("confidence_eval", confidence_evaluation_node)
    workflow.add_node("decision", decision_node)
    def human_pause_node(state):
        return state

    workflow.add_node("human_pause", human_pause_node) # Identity node for human breakpoint
    workflow.add_node("data_flywheel", data_flywheel_node)

    # Entry point
    workflow.set_entry_point("pre_filter")

    # Conditional Routing from Pre-Filter
    def route_after_pre_filter(state: AgentState):
        if state.get("early_blocked"):
            return "data_flywheel"
        return "extractor"

    workflow.add_conditional_edges(
        "pre_filter",
        route_after_pre_filter,
        {"data_flywheel": "data_flywheel", "extractor": "extractor"}
    )

    # Linear flow
    workflow.add_edge("extractor", "policy_engine")
    workflow.add_edge("policy_engine", "signal_builder")
    workflow.add_edge("signal_builder", "rag")
    workflow.add_edge("rag", "risk_aggregator")
    workflow.add_edge("risk_aggregator", "llm_explainer")
    workflow.add_edge("llm_explainer", "confidence_eval")
    workflow.add_edge("confidence_eval", "decision")

    def route_post_decision(state: AgentState):
        if state.get("requires_human_intervention"):
            return "human_pause"
        return "data_flywheel"

    workflow.add_conditional_edges(
        "decision",
        route_post_decision,
        {"human_pause": "human_pause", "data_flywheel": "data_flywheel"}
    )

    workflow.add_edge("human_pause", "data_flywheel")
    workflow.add_edge("data_flywheel", END)

    # Memory Checkpointer
    checkpointer = MemorySaver()

    # Compile with conditional human inspection breakpoint
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_pause"]
    )
