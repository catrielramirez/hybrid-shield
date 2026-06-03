import pytest
import logging
from dotenv import load_dotenv
load_dotenv()

from backend.agents.moderator.services.rag_service import rag_service

# Configuración de logs para ver detalles durante la ejecución del test
logger = logging.getLogger("moderation_pipeline")

@pytest.mark.asyncio
class TestRagServiceIntegration:
    """
    Suite de pruebas de integración para el servicio RAG (Vertex AI Search).
    
    Estrategia:
    - Ejecución real contra el endpoint de Google Cloud (v1beta).
    - Validación de contratos de datos (tipos y estructuras).
    - Verificación de la lógica de procesamiento asíncrono.
    """

    async def test_search_policies_standard_flow(self):
        """
        Valida que una búsqueda estándar de políticas devuelva contexto y citaciones formateadas.
        Fuerza la validación de contenido para asegurar que el Data Store no esté vacío.
        """
        # Query de prueba basada en categorías comunes de marketplace
        test_query = "Artículos completamente prohibidos"
        
        print(f"\n[RUNNING] Ejecutando búsqueda real para: '{test_query}'")
        rag_context, policy_citations = await rag_service.search_policies(test_query)
        
        # 1. Validaciones de tipo
        assert isinstance(rag_context, str), "El contexto RAG debe ser un string acumulado."
        assert isinstance(policy_citations, list), "Las citaciones deben ser una lista."
        
        # 2. Validación de contenido real obligatoria (Prueba de fuego)
        print(f"[INFO] Citaciones recuperadas: {len(policy_citations)}")
        assert len(policy_citations) > 0, "ERROR CRÍTICO: El RAG está conectado pero no devolvió ninguna política para esta query. El Data Store podría estar vacío."
        
        print(f"[SUCCESS] Se encontraron {len(policy_citations)} citaciones relevantes.")
        
        # Validar integridad del esquema de la primera citación
        citation = policy_citations[0]
        required_keys = {"policy_id", "policy_title", "snippet", "relevance_score"}
        assert required_keys.issubset(citation.keys()), f"Faltan claves en la citación: {required_keys - citation.keys()}"
        
        # Validar que el contexto contenga texto de los snippets
        assert citation["snippet"] in rag_context, "El fragmento de la citación debería estar en el contexto acumulado."
        assert citation["relevance_score"] >= 0, "El score de relevancia no puede ser negativo."

    async def test_search_policies_limit_logic(self):
        """
        Verifica que el servicio respete el límite máximo de 3 citaciones configurado en la lógica.
        """
        # Una query genérica para forzar múltiples resultados
        broad_query = "ecommerce policies safety rules contact"
        
        _, policy_citations = await rag_service.search_policies(broad_query)
        
        assert len(policy_citations) <= 3, f"El servicio retornó {len(policy_citations)} citaciones, excediendo el límite de 3."

    async def test_search_policies_error_handling_robustness(self):
        """
        Verifica que el servicio maneje entradas inesperadas sin lanzar excepciones no controladas.
        """
        # Caso: Query extremadamente larga o con caracteres especiales
        weird_query = "!!!" * 100
        
        try:
            rag_context, policy_citations = await rag_service.search_policies(weird_query)
            assert isinstance(rag_context, str)
            assert isinstance(policy_citations, list)
        except Exception as e:
            pytest.fail(f"El servicio lanzó una excepción no controlada ante una query inusual: {e}")

if __name__ == "__main__":
    # Permite ejecución directa con 'pytest -v -s'
    pytest.main(["-v", "-s", __file__])