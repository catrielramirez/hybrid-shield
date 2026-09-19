import sys
import os
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from vertexai.preview import reasoning_engines
import vertexai
import config

PROJECT_ID = config.get_project_id()
LOCATION = config.get_reasoning_engine_location()
vertexai.init(project=PROJECT_ID, location=LOCATION)

# ID del motor de razonamiento (Reasoning Engine) que acabamos de desplegar
REASONING_ENGINE_ID = config.get_reasoning_engine_id()

print(f"Cargando Reasoning Engine: {REASONING_ENGINE_ID}")
remote_agent = reasoning_engines.ReasoningEngine(f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}")

print("Ejecutando agente remoto...")
response = remote_agent.query(
    input_data={
        "title": "piloto de lluvia para perro",
        "description": "Tenemos modelos y talles variados",
        "price": 45000,
        "gcs_uri": "gs://ecommerce-police-media-uploads/items/0e2bdd72-0ded-43d5-abea-b94740732f7c/optimized_image.webp",
        "thread_id": "test_thread_12456"
    }
)

print("\n--- Respuesta del Agente ---")
try:
    print(json.dumps(response, indent=4, ensure_ascii=False))
except Exception as e:
    print("No se pudo parsear a JSON. Respuesta raw:")
    print(response)
