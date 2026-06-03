import pytest
from unittest.mock import patch, MagicMock

from backend.agents.moderator.services.ai_service import (
    analyze_safety,
    extract_multimodal_features
)


class TestAIService:

    @pytest.mark.asyncio
    async def test_safety_analysis(self):
        """Llamada real a Gemini usando await."""
        result = await analyze_safety(
            "Venta de explosivos",
            "Producto peligroso",
            model_name="gemini-2.5-flash-lite"
        )
        assert result["data"].get("is_critical") is True
        assert "usage" in result
        assert "prompt_tokens" in result["usage"]

    @pytest.mark.asyncio
    async def test_safety_analysis_error_handling(self):
        """Verifica que los errores de API devuelvan estructura correcta."""
        with patch(
            "backend.agents.moderator.services.ai_service.get_gemini_model",
            side_effect=Exception("API Error")
        ):
            result = await analyze_safety("título", "descripción")
            assert result["data"]["status"] == "error"
            assert result["data"]["is_critical"] is None
            assert result["usage"]["prompt_tokens"] == 0

    @pytest.mark.asyncio
    async def test_multimodal_extraction(self, real_gcs_uri, product_sample):
        """Prueba de visión con Gemini usando await."""
        result = await extract_multimodal_features(
            real_gcs_uri,
            product_sample,
            model_name="gemini-2.5-flash-lite"
        )
        assert "is_sellable" in result["data"]
        assert "usage" in result
        assert "prompt_tokens" in result["usage"]

    @pytest.mark.asyncio
    async def test_multimodal_extraction_error_handling(self, product_sample):
        """Verifica que los errores de extracción devuelvan estructura correcta."""
        with patch(
            "backend.agents.moderator.services.ai_service.resolve_gcs_uri",
            side_effect=Exception("GCS Error")
        ):
            result = await extract_multimodal_features(
                "gs://bucket/imagen.jpg",
                product_sample,
            )
            assert result["data"]["status"] == "error"
            assert result["data"]["is_sellable"] is None
            assert result["data"]["error"] == "multimodal_analysis_failed"