import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

load_dotenv()

def listar_recursos():
    # Inicializa el cliente usando las credenciales del entorno
    client = discoveryengine.EngineServiceClient()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    # Define la ruta base en la ubicacion global
    parent = f"projects/{project_id}/locations/global/collections/default_collection"
    
    print(f"--- Buscando Aplicaciones en el proyecto: {project_id} ---")
    
    try:
        engines = client.list_engines(parent=parent)
        encontrado = False
        for engine in engines:
            encontrado = True
            # Extrae el ID final de la ruta del recurso
            engine_id = engine.name.split('/')[-1]
            print("\nAPP ENCONTRADA")
            print(f"Nombre visible: {engine.display_name}")
            print(f"ID para tu .env: {engine_id}")
        
        if not encontrado:
            print("\nNo se encontraron Apps. Verifica que creaste una App de Busqueda en la consola.")
            
    except Exception as e:
        print(f"\nError al conectar: {e}")

if __name__ == "__main__":
    listar_recursos()