import pytest
from backend.agents.moderator.nodes import rag_node, risk_evaluator_node, llm_reasoning_node
from backend.agents.moderator.state import AgentState

@pytest.mark.asyncio
async def test_rag_node_integration(unique_id):
    """Verifica la integración con el servicio RAG."""
    state = {
        "thread_id": unique_id,
        "features": {"primary_object": "productos prohibidos"}
    }

    result = await rag_node(state, {"configurable": {"thread_id": unique_id}})

    assert "rag_context" in result
    assert "policy_citations" in result
    assert "rag" in result["execution_metrics"]["nodes"]
    
    for citation in result.get("policy_citations", []):
        assert "reason" not in citation

@pytest.mark.asyncio
@pytest.mark.parametrize("objeto, keyword", [
    ("medicamentos", "articulos_prohibidos"),
    ("armas de fuego", "articulos_prohibidos")
])
async def test_rag_safety_layer_consistency(unique_id, objeto, keyword):
    state = {"thread_id": unique_id, "features": {"primary_object": objeto}}
    result = await rag_node(state, {"configurable": {"thread_id": unique_id}})
    
    citas = result.get("policy_citations", [])
    if citas:
        assert any(keyword in c["policy_title"].lower() for c in citas)

@pytest.mark.asyncio
async def test_risk_evaluator_node(unique_id):
    """Verifica procesamiento de señales y cálculo de score."""
    state = {
        "input_data": {"title": "Macbook Pro", "price": 10.0},
        "features": {
            "primary_object": "laptop",
            "object_category": "electronics",
            "image_quality": "low"
        },
        "min_market_price": 500.0,
        "max_market_price": 3000.0
    }
    
    result = await risk_evaluator_node(state, {"configurable": {"thread_id": unique_id}})
    
    assert result["signals"]["price_anomaly"] is True
    assert result["signals"]["low_quality_image"] is True
    assert result["risk_score"] > 0.0
    assert "risk_evaluator" in result["execution_metrics"]["nodes"]

@pytest.mark.asyncio
async def test_llm_reasoning_node(unique_id):
    """Verifica generación de reasoning JSON."""
    state = {
        "input_data": {"title": "Test Product"},
        "policy_citations": [{"policy_id": "POL-1", "policy_title": "Test", "snippet": "..."}],
        "risk_score": 0.7,
        "signals": {"external_contact": True},
        "risk_breakdown": [{"factor": "external_contact", "weight": 1.0}]
    }
    
    result = await llm_reasoning_node(state, {"configurable": {"thread_id": unique_id}})
    
    assert len(result.get("reasoning", "")) > 0
    assert isinstance(result.get("policy_violations"), list)
    assert "reasoning" in result["execution_metrics"]["nodes"]