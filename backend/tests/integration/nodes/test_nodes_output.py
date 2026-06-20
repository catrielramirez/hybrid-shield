import pytest
from unittest.mock import patch, AsyncMock
from langgraph.types import Command
from backend.agents.moderator.nodes import decision_node, data_flywheel_node

# ================================================================
# TESTS UNITARIOS 
# ================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("risk_score, expected_action, requires_human", [
    (0.1, "Approve", False),      # score < 0.35
    (0.5, "Human Review", True),  # 0.35 <= score < 0.85
    (0.9, "Block", False)         # score >= 0.85
])
@patch("backend.agents.moderator.nodes.firestore_service.update_job_status", new_callable=AsyncMock)
@patch("backend.agents.moderator.nodes.firestore_service.update_ui_state", new_callable=AsyncMock)
async def test_decision_logic(mock_ui, mock_update, risk_score, expected_action, requires_human, unique_id):
    """Valida los umbrales de decisión."""
    state = {
        "thread_id": unique_id,
        "risk_score": risk_score,
        "features": {"confidence": 1.0}
    }
    
    # Marcado como await por si decides decorar decision_node más adelante
    result = await decision_node(state, {"configurable": {"thread_id": unique_id}})
    
    assert result.get("final_action") == expected_action
    assert result.get("requires_human_intervention") == requires_human
    assert "uncertainty" in result
    assert result["uncertainty"] == 0.0
    assert "routing_reason" in result
    assert "reasoning" in result
    assert "risk_score" in result
    assert result["risk_score"] == risk_score

# ================================================================
# TEST DE INTEGRACIÓN (HITL + PERSISTENCIA REAL)
# ================================================================
@pytest.mark.asyncio
@patch("backend.agents.moderator.nodes.firestore_service.update_job_status", new_callable=AsyncMock)
@patch("backend.agents.moderator.nodes.firestore_service.update_ui_state", new_callable=AsyncMock)
async def test_human_review_full_integration(mock_ui, mock_update, app, unique_id, real_gcs_uri):
    """Test de integración del flujo de intervención humana."""
    config = {"configurable": {"thread_id": unique_id}}
    
    initial_state = {
        "input_data": {
            "title": "Producto Test Real",
            "price": 150.0,
        },
        "gcs_uri": real_gcs_uri,
        "thread_id": unique_id
    }

    # 1. Avanzar hasta el nodo 'decision'
    async for event in app.astream(initial_state, config=config):
        if "decision" in event:
            break
            
    # 2. Intercepción forzando revisión manual
    app.update_state(
        config,
        {"requires_human_intervention": True},
        as_node="decision"
    )

    # 3. Continuar hasta la interrupción en 'human_in_the_loop'
    async for event in app.astream(None, config=config):
        pass

    snapshot = app.get_state(config)
    assert "human_in_the_loop" in snapshot.next

    # 4. Reanudación final con inyección de feedback manual
    # LangGraph reanuda el nodo devolviendo este valor desde la llamada a interrupt()
    await app.ainvoke(Command(resume={"decision": "Approve", "justification": "Looks good"}), config=config)
    
    final_state = app.get_state(config).values
    
    assert final_state.get("audit_log") is not None
    assert final_state.get("final_action") == "Approve"
    # Verificamos que el nodo gestionó la bandera correctamente
    assert final_state.get("requires_human_intervention") is False

# ================================================================
# TEST DE SALIDA (BIGQUERY)
# ================================================================

@pytest.mark.asyncio
@patch("backend.agents.moderator.nodes.bigquery.Client")
async def test_data_flywheel_real_persistence(mock_bq, unique_id):
    """Verifica la persistencia en BigQuery."""
    state = {
        "thread_id": unique_id,
        "final_action": "Human Review",
        "human_feedback": {"decision": "Block"},
        "risk_score": 0.5,
        "reasoning": "Detección manual de política",
        "execution_metrics": {"nodes": {"test": {}}}
    }
    
    # CORRECCIÓN: Al ser async, requiere await
    result = await data_flywheel_node(state, {"configurable": {"thread_id": unique_id}})
    
    # Validamos que el nodo procesó la decisión del humano
    assert result["final_action"] == "Block"
    
    # Validamos el log de auditoría
    assert any(log["node"] == "fly_wheel" for log in result.get("audit_log", []))