import os
import json
from dotenv import load_dotenv
from google.cloud import discoveryengine
from google.api_core import exceptions

def test_vertex_ai_search():
    # Cargar variables de entorno
    load_dotenv()
    
    raw_location = os.getenv("GOOGLE_CLOUD_LOCATION")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = raw_location if raw_location else "global"
    data_store_id = os.getenv("DATA_STORE_ID")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    print("--- Verificando Entorno ---")
    print(f"Project ID: {project_id}")
    print(f"Location: {location}")
    print(f"Data Store ID: {data_store_id}")
    print(f"Credentials Path: {credentials_path}")

    if not all([project_id, location, data_store_id, credentials_path]):
        print("Error: Faltan variables de entorno en el archivo .env")
        return

    # Lista de ubicaciones para probar
    locations_to_try = [location]
    for fallback in ["global", "us-central1", "us"]:
        if fallback not in locations_to_try:
            locations_to_try.append(fallback)

    for loc in locations_to_try:
        print(f"\n--- Probando Ubicación: {loc} ---")
        try:
            # Configurar el endpoint según la ubicación
            api_endpoint = "discoveryengine.googleapis.com" if loc == "global" else f"{loc}-discoveryengine.googleapis.com"
            client_options = {"api_endpoint": api_endpoint}
            
            # Inicializar el cliente (CORREGIDO: se eliminó 'cions=' y 'exlient_optceptions')
            client = discoveryengine.SearchServiceClient(client_options=client_options)

            # Construcción manual de la ruta (Serving Config)
            serving_config = f"projects/{project_id}/locations/{loc}/collections/default_collection/engines/{data_store_id}/servingConfigs/default_search"

            request = discoveryengine.SearchRequest(
                serving_config=serving_config,
                query="requisitos de imágenes",
                page_size=3,
            )

            response = client.search(request)

            print(f"--- ¡Conexión Exitosa en {loc}! ---")
            for i, result in enumerate(response.results):
                print(f"\nResultado {i+1}:")
                derived_data = result.document.derived_struct_data
                if derived_data and "snippets" in derived_data:
                    for j, snippet in enumerate(derived_data["snippets"]):
                        print(f"Snippet {j+1}: {snippet.get('snippet', 'N/A')}")
            
            return # Salir si tuvo éxito

        except exceptions.NotFound:
            print(f"Recurso no encontrado en {loc}. Probando siguiente...")
        except Exception as e:
            print(f"Error en {loc}: {e}")
            continue

if __name__ == "__main__":
    test_vertex_ai_search()