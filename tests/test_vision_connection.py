import os
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv
import json

# Cargar variables de entorno
load_dotenv()

RESOURCE_ID = os.getenv("REASONING_ENGINE_RESOURCE_ID")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not RESOURCE_ID:
    print("Error: REASONING_ENGINE_RESOURCE_ID no encontrado en .env")
    exit(1)

# Inicializar Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

print(f"--- Probando Conexión de Visión con Reasoning Engine ---")
print(f"Resource ID: {RESOURCE_ID}")

# Inicializar el motor remoto
remote_engine = reasoning_engines.ReasoningEngine(RESOURCE_ID)

# Petición según formato solicitado por el usuario
# Nota: Mapeamos los campos a la estructura que el Grafo espera (input_data y gcs_uri)
user_test_data = {
    "remote_path": "gs://ecommerce-police-policies-ecommerce-police-portfolio/imagenes_ingesta/item_03.png", 
    "text": "Sony WH-1000XM5"
}

# Estructura interna del agente
agent_input = {
    "input_data": {
        "title": user_test_data["text"],
        "description": "Prueba de validación de visión desde script de test.",
        "price": 350.0 # Precio de mercado estimado
    },
    "gcs_uri": user_test_data["remote_path"],
    "thread_id": "test-vision-agent",
    "audit_log": [],
    "requires_human_intervention": False,
    "early_blocked": False
}

print(f"Enviando URI: {user_test_data['remote_path']}")
print(f"Enviando Texto: {user_test_data['text']}")

try:
    # Ejecutar la consulta
    # El método query del ModeratorAgent recibe input_data como estado inicial
    response = remote_engine.query(input_data=agent_input)
    
    print("\n Ejecución terminada correctamente.")
    
    # Extraer información de interés
    features = response.get("features", {})
    final_action = response.get("final_action", "N/A")
    reasoning = response.get("reasoning", "N/A")
    
    print(f"\n--- Resultado del Análisis ---")
    print(f"Acción Final: {final_action}")
    print(f"Objeto Detectado: {features.get('primary_object', 'No identificado')}")
    print(f"Categoría: {features.get('object_category', 'N/A')}")
    print(f"Sellable: {features.get('is_sellable', 'N/A')}")
    print(f"Calidad de Imagen: {features.get('image_quality', 'N/A')}")
    print(f"\nExplicación (LLM): {reasoning}")
    
    # Verificar si el agente logró leer la imagen
    if features.get("error") == "gcs_access_failed":
        print("\n ERROR: El agente NO pudo acceder a la imagen en el bucket.")
        print("Sugerencia: Revisa los permisos (IAM) de la Service Account de Vertex AI.")
    elif not features:
        print("\n ADVERTENCIA: No se extrajeron características (features). Posible error en el procesamiento multimodal.")
    else:
        print("\n El agente leyó la imagen correctamente y extrajo características.")

except Exception as e:
    print(f"\n Error fatal durante la llamada al Reasoning Engine: {e}")
    if "403" in str(e) or "Access Denied" in str(e):
        print("\nTIP: Parece un error de permisos (403).")
        print(f"Asegúrate de que la Service Account de Vertex AI tenga roles/storage.objectViewer en el bucket.")
