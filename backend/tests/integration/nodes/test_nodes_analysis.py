import pytest
from backend.agents.moderator.nodes import pre_filter_node, feature_extractor_node, risk_evaluator_node

@pytest.mark.asyncio
async def test_pre_filter_node_offensive(unique_id):
    """Testea que un input ofensivo retorne early_blocked: True."""
    # El pre-filtro solo necesita input_data y thread_id
    state = {
        "input_data": {
            "title": "Venta de drogas ilegales",
            "description": "Ofrezco sustancias prohibidas y narcóticos al mejor precio."
        },
        "thread_id": unique_id
    }
    
    result = await pre_filter_node(state, {"configurable": {"thread_id": unique_id}})
    assert result.get("early_blocked") is True
    assert "Bloqueo automático" in result.get("reasoning", "")
    assert "execution_metrics" in result

@pytest.mark.asyncio
async def test_feature_extractor_node(real_gcs_uri, product_sample, unique_id):
    """Testea que al pasar una URI de GCS real, el retorno contenga features y límites."""
    # El extractor solo requiere los datos de entrada, la uri de la imagen y el id del hilo
    state = {
        "input_data": product_sample,
        "gcs_uri": real_gcs_uri,
        "thread_id": unique_id
    }
    
    result = await feature_extractor_node(state, {"configurable": {"thread_id": unique_id}})
    assert "features" in result
    assert "min_market_price" in result
    assert "max_market_price" in result
    assert "image_quality_score" in result

@pytest.mark.asyncio
async def test_risk_evaluator_node_price_anomaly(unique_id):
    """Verifica que los límites dinámicos disparen price_anomaly."""
    # El evaluador de riesgo no es async, solo lee features, input_data y los límites calculados
    state = {
        "input_data": {
            "title": "Macbook Pro 2023",
            "price": 10.0
        },
        "features": {
            "primary_object": "laptop",
            "object_category": "electronics"
        },
        "min_market_price": 500.0,
        "max_market_price": 3000.0,
        "thread_id": unique_id
    }
    
    result = await risk_evaluator_node(state, {"configurable": {"thread_id": unique_id}})
    signals = result.get("signals", {})
    assert signals.get("price_anomaly") is True
    assert result.get("risk_score") > 0.0