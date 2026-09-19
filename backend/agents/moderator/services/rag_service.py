import logging
import asyncio
from google.cloud import discoveryengine_v1beta as discoveryengine
import config

logger = logging.getLogger("moderation_pipeline")

class RagService:
    """
    Servicio profesional para interactuar con Vertex AI Search (Discovery Engine)
    de forma asíncrona, optimizando la latencia del grafo.
    """
    def __init__(self):
        self._client = None

    @property
    def project_id(self) -> str:
        return config.get_project_id()

    @property
    def location(self) -> str:
        return config.get_location()

    @property
    def data_store_id(self) -> str | None:
        return config.get_data_store_id()

    @property
    def engine_id(self) -> str | None:
        return config.get_engine_id()

    @property
    def serving_config(self) -> str:
        return (
            f"projects/{self.project_id}/locations/global/collections/default_collection"
            f"/engines/{self.engine_id}/servingConfigs/default_search"
        )

    def _sync_search_policies(self, query: str) -> tuple[str, list[dict]]:
        """
        Ejecuta una búsqueda semántica en el Data Store de políticas de forma síncrona.
        Este método está diseñado para ser ejecutado en un thread separado.
        """
        if not self.data_store_id:
            logger.warning("RAG_SERVICE: DATA_STORE_ID no configurado. Saltando búsqueda.")
            return "Contexto no disponible por falta de configuración.", []

        # Instanciamos el cliente síncrono oficial (lazy init para reusar conexión)
        if self._client is None:
            self._client = discoveryengine.SearchServiceClient()
        client = self._client
        rag_context = ""
        policy_citations = []

        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=query,
                page_size=3,
            )
            # Invocación síncrona
            response_pager = client.search(request)
            idx = 0
            # Iteración síncrona
            for result in response_pager:
                derived_data = result.document.derived_struct_data
                if not derived_data:
                    derived_data = {}
                # pyrefly: ignore [missing-attribute]
                doc_title = derived_data.get("title", "Untitled Policy")
                
                # Lista de tuplas (texto_fragmento, score_relevancia)
                snippets_list = []
                
                # 1. Caso: snippets estándar (llave 'snippets', subllave 'snippet')
                if "snippets" in derived_data:
                    # pyrefly: ignore [not-iterable]
                    for s in derived_data["snippets"]:
                        # pyrefly: ignore [missing-attribute]
                        text = s.get("snippet", "")
                        # pyrefly: ignore [missing-attribute]
                        score = s.get("snippet_score", 0.0)
                        if text:
                            snippets_list.append((text, score))
                            
                # 2. Caso: respuestas extractivas (llave 'extractive_answers', subllave 'content')
                elif "extractive_answers" in derived_data:
                    # pyrefly: ignore [not-iterable]
                    for a in derived_data["extractive_answers"]:
                        # pyrefly: ignore [missing-attribute]
                        text = a.get("content", "")
                        if text:
                            snippets_list.append((text, 1.0)) # Usamos 1.0 por defecto
                            
                # 3. Caso: segmentos extractivos (llave 'extractive_segments', subllave 'content')
                elif "extractive_segments" in derived_data:
                    # pyrefly: ignore [not-iterable]
                    for seg in derived_data["extractive_segments"]:
                        # pyrefly: ignore [missing-attribute]
                        text = seg.get("content", "")
                        if text:
                            snippets_list.append((text, 1.0))

                for snippet_text, relevance in snippets_list:
                    relevance = round(relevance, 3)
                    rag_context += snippet_text + "\n"
                    policy_citations.append({
                        "policy_id": f"POL-{idx + 1}",
                        "policy_title": doc_title,
                        "snippet": snippet_text,
                        "reason": "",
                        "relevance_score": relevance,
                    })
                idx += 1
                if idx >= 3: # Limitamos a top 3 resultados manualmente si el pager trae más
                    break
                    
        except Exception as e:
            logger.error(f"RAG_SERVICE: Error crítico en búsqueda síncrona: {e}")
            rag_context = "Error técnico al recuperar políticas de seguridad."
            
        # Refinamiento final: ordenamos por relevancia y truncamos
        policy_citations = sorted(policy_citations, key=lambda c: c["relevance_score"], reverse=True)[:3]
        
        return rag_context, policy_citations

    async def search_policies(self, query: str) -> tuple[str, list[dict]]:
        """
        Delega la búsqueda vectorial a un thread separado mediante asyncio.to_thread
        para asegurar que el SDK no bloquee el event loop principal bajo ninguna circunstancia.
        """
        return await asyncio.to_thread(self._sync_search_policies, query)

# Exportamos una instancia lista para usar (Singleton Pattern)
rag_service = RagService()
